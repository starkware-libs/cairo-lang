import dataclasses
import itertools
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import field
from typing import Callable, Dict, List, Optional

import marshmallow.fields as mfields

from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import (
    RegChange, RegChangeLike, RegTrackingData)
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName, ScopedNameAsStr


@dataclasses.dataclass
class ReferenceManager:
    references: List[Reference] = field(default_factory=list)

    def alloc_id(self, reference: Reference) -> int:
        self.references.append(reference)
        return len(self.references) - 1

    def get_ref(self, ref_id: int) -> Reference:
        return self.references[ref_id]


class FlowTrackingData(ABC):
    """
    Tracking data representing the values of the references in a specific location in the program,
    considering all possible flows that may reach there.
    """
    @abstractmethod
    def converge(
            self, reference_manager: ReferenceManager, other: 'FlowTrackingData',
            group_alloc: Callable):
        """
        Returns a new tracking data representing all references that are valid coming from either
        self or from other.
        """

    @abstractmethod
    def resolve_reference(self, reference_manager: ReferenceManager, name: ScopedName) -> Reference:
        """
        Returns the reference specified by the full identifier name, taking into account the
        current context and rebindings.
        Throws FlowTrackingError if the reference is revoked.
        """


@dataclasses.dataclass(frozen=True)
class FlowTrackingDataUnreachable(FlowTrackingData):
    """
    An unreachable tracking data. Represents a case where there are no flows reaching
    this specific location in the program.
    """

    def converge(
            self, reference_manager: ReferenceManager, other: 'FlowTrackingData',
            group_alloc: Callable):
        return other

    def resolve_reference(self, reference_manager: ReferenceManager, name: ScopedName) -> Reference:
        raise FlowTrackingError(f'Reference {name} revoked.')


@dataclasses.dataclass(frozen=True)
class FlowTrackingDataActual(FlowTrackingData):
    """
    Tracking data for a reachable location in the program.
    """
    # Current ap tracking.
    ap_tracking: RegTrackingData
    # Mapping from full reference name to the Reference instance.
    reference_ids: Dict[ScopedName, int] = field(
        metadata=dict(
            marshmallow_field=mfields.Dict(keys=ScopedNameAsStr, values=mfields.Integer())),
        default_factory=dict)

    @classmethod
    def new(cls, group_alloc: Callable) -> 'FlowTrackingDataActual':
        return cls(
            ap_tracking=RegTrackingData.new(group_alloc),
        )

    def resolve_reference(self, reference_manager: ReferenceManager, name: ScopedName) -> Reference:
        ref_id = self.reference_ids.get(name)
        if ref_id is None:
            raise FlowTrackingError(f'Reference {name} revoked.')
        return reference_manager.get_ref(ref_id)

    def converge(
            self, reference_manager: ReferenceManager, other: 'FlowTrackingData',
            group_alloc: Callable):
        if not isinstance(other, FlowTrackingDataActual):
            return other.converge(reference_manager, self, group_alloc)

        new_ap_tracking = self.ap_tracking.converge(other.ap_tracking, group_alloc)
        simplifier = ExpressionSimplifier()

        # Allow different references from different branches to unite if they have the same name
        # and the same expression at the converged ap_tracking.
        reference_ids = {}
        for name, ref_id in self.reference_ids.items():
            other_ref_id = other.reference_ids.get(name)
            if other_ref_id is None:
                continue
            reference = reference_manager.get_ref(ref_id)
            other_ref = reference_manager.get_ref(other_ref_id)
            try:
                ref_expr = reference.eval(self.ap_tracking)
                if simplifier.visit(ref_expr) == \
                        simplifier.visit(other_ref.eval(other.ap_tracking)):
                    # Same expression.
                    # Create a new reference on the new ap tracking.
                    new_reference = Reference(
                        pc=reference.pc,
                        value=ref_expr,
                        ap_tracking_data=new_ap_tracking,
                        locations=reference.locations + other_ref.locations,
                    )
                    ref_id = reference_manager.alloc_id(new_reference)
                    reference_ids[name] = ref_id
            except FlowTrackingError:
                pass

        return FlowTrackingDataActual(
            ap_tracking=new_ap_tracking,
            reference_ids=reference_ids,
        )

    def add_ap(self, ap_change: RegChangeLike, group_alloc: Callable) -> 'FlowTrackingData':
        new_ap_tracking = self.ap_tracking.add(ap_change, group_alloc)
        return dataclasses.replace(self, ap_tracking=new_ap_tracking)

    def add_reference(
            self, reference_manager: ReferenceManager, name: ScopedName,
            ref: Reference) -> 'FlowTrackingData':
        """
        Adds or rebinds a reference.
        """
        ref_id = reference_manager.alloc_id(ref)
        return dataclasses.replace(
            self,
            reference_ids={**self.reference_ids, name: ref_id},
        )


@dataclasses.dataclass(frozen=True)
class InstructionFlows:
    """
    Specifies flows from an instruction to other instructions.
    Each flow is characterized by the destination instruction, and the register changes in that
    flow.

    Example:
    'ap += 3' has a flow to the next instruction, where the ap is changed by +3.
    'ret' has no flow to the next instruction.
    'jmp lbl' has only a flow to 'lbl'.
    'jmp lbl if [ap] != 0' has a flow to 'lbl' and to the next instruction.
    """

    # next_inst is the flow to the next instruction. None means there is no flow.
    # InstructionFlows() is an instruction with no known flow.
    next_inst: Optional[RegChange] = None
    # jumps is the possible flows to other locations in the program, represetned as fully qualified
    # names of labels.
    jumps: Dict[ScopedName, RegChange] = field(default_factory=dict)


class FlowTracking:
    """
    Tracks the progress of ap during a run.
    """

    def __init__(self):
        # Current flow tracking data. FlowTrackingDataUnreachable means the currect position is
        # unreachable - has no flow. For example, between a ret and another instruction.
        self.data: FlowTrackingData = FlowTrackingDataUnreachable()
        # Mapping from a fully qualified label name to its tracking data.
        # This begines unconstrained, and for every flow to this label, we 'converge' this data
        # with the new tracking data.
        self.labels_data: Dict[ScopedName, FlowTrackingData] = \
            defaultdict(FlowTrackingDataUnreachable)
        self.groups = itertools.count(0)
        self.reference_manager = ReferenceManager()

    def get(self) -> FlowTrackingDataActual:
        """
        Retrieves the current tracking data. If there is no current flow, allocates a new tracking
        data for the new flow.
        """
        if self.data == FlowTrackingDataUnreachable():
            self.data = FlowTrackingDataActual.new(group_alloc=self._group_alloc)
        assert isinstance(self.data, FlowTrackingDataActual)
        return self.data

    def get_ap_tracking(self) -> RegTrackingData:
        return self.get().ap_tracking

    def add_flow_to_label(self, label_name: ScopedName, ap_change: RegChangeLike):
        """
        Registers a flow from current location to a label, with some ap_change.
        For example, after 'jmp label1 if [ap] != 0; ap++', we have a flow to label1 with ap_change
        of 1.
        """
        ap_change = RegChange.from_expr(ap_change)
        new_data = self.get().add_ap(ap_change, self._group_alloc)
        self.labels_data[label_name] = self.labels_data[label_name].converge(
            self.reference_manager, new_data, self._group_alloc)

    def converge_with_label(self, label_name: ScopedName):
        """
        Registers a convergence of current flow with a label. This happens when we get to that
        label's definition location.
        """
        self.data = self.data.converge(
            self.reference_manager, self.labels_data[label_name], self._group_alloc)

    def revoke(self):
        self.data = FlowTrackingDataUnreachable()

    def has_flow(self):
        """
        Returns whether the current position has an active flow. For example, after a ret
        instruction, before next instruction, we have no active flow.
        """
        return self.data is not None

    def _group_alloc(self) -> int:
        """
        Allocates a new group for RegTrackingData. See RegTrackingData.
        """
        return next(self.groups)

    def add_ap(self, ap_change: RegChangeLike):
        ap_change = RegChange.from_expr(ap_change)
        self.data = self.get().add_ap(ap_change, self._group_alloc)

    def add_reference(self, name: ScopedName, ref: Reference):
        self.data = self.get().add_reference(self.reference_manager, name, ref)

    def resolve_reference(self, name: ScopedName) -> Reference:
        return self.data.resolve_reference(self.reference_manager, name)
