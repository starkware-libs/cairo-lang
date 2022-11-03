import dataclasses
import itertools
import re
from typing import Dict, Iterable, List, Optional, Tuple

from starkware.cairo.lang.compiler.debug_info import InstructionLocation
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_definition import (
    IdentifierDefinition,
    ReferenceDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual
from starkware.cairo.lang.compiler.preprocessor.preprocessor import AttributeScope
from starkware.cairo.lang.compiler.program import CairoHint, Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName


@dataclasses.dataclass
class IdentifierInfo:
    name: ScopedName
    identifier_definition: IdentifierDefinition
    reference_id: int


def get_identifiers(
    identifier_manager: IdentifierManager,
    names: Iterable[str],
    accessible_scopes: List[ScopedName],
    flow_tracking_data: FlowTrackingDataActual,
) -> List[IdentifierInfo]:
    """
    Returns an IdentifierInfo for each of the given identifiers.
    The identifier's name is resolved based on the given accessible_scopes and flow_tracking_data.
    """
    result = []
    for name in names:
        search_res = identifier_manager.search(
            accessible_scopes=accessible_scopes,
            name=ScopedName.from_string(name),
        )
        if not isinstance(search_res.identifier_definition, ReferenceDefinition):
            # Only return reference identifiers. Other identifiers are not being filtered anyway.
            continue
        reference_id = flow_tracking_data.get_reference_id(search_res.canonical_name)
        assert reference_id is not None
        result.append(
            IdentifierInfo(
                name=search_res.canonical_name,
                identifier_definition=search_res.identifier_definition,
                reference_id=reference_id,
            )
        )
    return result


def get_hint_identifiers(
    hint: CairoHint, identifier_manager: IdentifierManager, location: Optional[InstructionLocation]
) -> List[IdentifierInfo]:
    """
    Returns identifiers that are referenced in the given hint.
    """
    referenced_identifiers = re.findall(r"\bids.([a-zA-Z_0-9.]+)", hint.code)

    # Make sure all mentions of 'ids' in the code, are accesses to the ids attributes
    # (i.e., "ids.<attribute>").
    # Other mentions can be passing 'ids' as an argument to a function, in which case we can't
    # discover all the identifiers used in the hint.
    if len(re.findall(r"\bids\b", hint.code)) != len(referenced_identifiers):
        raise LocationError(
            message="Unexpected use of 'ids' in a hint.",
            location=location.inst if location is not None else None,
        )

    return get_identifiers(
        identifier_manager=identifier_manager,
        names=set(referenced_identifiers),
        accessible_scopes=hint.accessible_scopes,
        flow_tracking_data=hint.flow_tracking_data,
    )


def get_attribute_identifiers(
    attribute: AttributeScope, identifier_manager: IdentifierManager
) -> List[IdentifierInfo]:
    """
    Returns identifiers that are referenced in the given attribute.
    """
    assert attribute.flow_tracking_data is not None
    referenced_identifiers = set(re.findall(r"{([a-zA-Z_0-9.]+)}", attribute.value))
    return get_identifiers(
        identifier_manager=identifier_manager,
        names=referenced_identifiers,
        accessible_scopes=attribute.accessible_scopes,
        flow_tracking_data=attribute.flow_tracking_data,
    )


def _filter_unused_references(program: Program) -> Tuple[Program, List[IdentifierInfo]]:
    """
    Returns a new Program object after filtering all the program hints and attributes from
    references that are not mentioned in them.
    Also returns a list of the mentioned references.
    """
    identifiers = []

    new_hints: Dict[int, List[CairoHint]] = {}
    for pc, hints in program.hints.items():
        new_hints[pc] = []
        for hint in hints:
            hint_identifiers = get_hint_identifiers(
                hint=hint,
                identifier_manager=program.identifiers,
                location=(
                    program.debug_info.instruction_locations.get(pc)
                    if program.debug_info is not None
                    else None
                ),
            )
            new_hints[pc].append(
                dataclasses.replace(
                    hint,
                    flow_tracking_data=hint.flow_tracking_data.filter_references(
                        names_to_keep=[identifier.name for identifier in hint_identifiers]
                    ),
                )
            )
            identifiers += hint_identifiers

    new_attributes = []
    for attribute in program.attributes:
        assert attribute.flow_tracking_data is not None
        attributes_identifiers = get_attribute_identifiers(
            attribute=attribute, identifier_manager=program.identifiers
        )
        new_attributes.append(
            dataclasses.replace(
                attribute,
                flow_tracking_data=attribute.flow_tracking_data.filter_references(
                    names_to_keep=[id.name for id in attributes_identifiers]
                ),
            )
        )
        identifiers += attributes_identifiers

    filtered_program = dataclasses.replace(program, hints=new_hints, attributes=new_attributes)

    return (filtered_program, identifiers)


def _filter_identifiers(program: Program, identifiers: List[IdentifierInfo]) -> Program:
    """
    Returns a modified program that holds the given identifiers and any non reference identifiers.
    """
    new_identifiers = IdentifierManager()
    for identifier in identifiers:
        new_identifiers.add_identifier(identifier.name, identifier.identifier_definition)
    for name, identifier_def in program.identifiers.as_dict().items():
        if not isinstance(identifier_def, ReferenceDefinition):
            new_identifiers.add_identifier(name, identifier_def)

    return dataclasses.replace(program, identifiers=new_identifiers)


def _filter_reference_manager(program: Program, identifiers: List[IdentifierInfo]) -> Program:
    """
    Returns a modified program that holds only the references of the given identifiers.
    Note: filtering references from the program's reference_manager causes the reference ids to
    change. Therefore, this function goes over the program relevant elements and fixes the
    reference ids.
    Note: the program hints and attributes are modified in place.
    """
    # Make a list of reference ids that should be kept.
    reference_ids_to_keep = sorted({identifier.reference_id for identifier in identifiers})

    # Create a map from the old reference id to the new one (after removing the unnecessary
    # references).
    old_to_new_ref_id = {
        old_ref_id: new_ref_id for new_ref_id, old_ref_id in enumerate(reference_ids_to_keep)
    }

    program = dataclasses.replace(
        program,
        reference_manager=program.reference_manager.filter_references(
            ref_ids_to_keep=reference_ids_to_keep
        ),
    )

    # Update the reference ids in the program hints.
    for hint in itertools.chain(*program.hints.values()):
        hint.flow_tracking_data = hint.flow_tracking_data.update_reference_ids(
            old_to_new_ref_id=old_to_new_ref_id
        )

    # Update the reference ids in the program attributes.
    for i, attribute in enumerate(program.attributes):
        assert attribute.flow_tracking_data is not None
        program.attributes[i] = dataclasses.replace(
            program.attributes[i],
            flow_tracking_data=attribute.flow_tracking_data.update_reference_ids(
                old_to_new_ref_id=old_to_new_ref_id
            ),
        )

    return program


def filter_unused_identifiers(program: Program) -> Program:
    """
    Filters unused identifiers and their corresponding reference ids from program.
    Unused identifiers are identifiers that are not referenced in any hint or attribute in the
    program.
    """
    filtered_program, identifiers = _filter_unused_references(program=program)
    filtered_program = _filter_identifiers(program=filtered_program, identifiers=identifiers)
    filtered_program = _filter_reference_manager(program=filtered_program, identifiers=identifiers)

    # Delete flow_tracking_data from the program's debug_info, as it is no longer in sync with the
    # new program identifiers.
    if filtered_program.debug_info is not None:
        new_inst_locations = {}
        for pc, inst in filtered_program.debug_info.instruction_locations.items():
            new_inst = dataclasses.replace(inst, flow_tracking_data=None)
            new_inst_locations[pc] = new_inst
        filtered_program.debug_info = dataclasses.replace(
            filtered_program.debug_info, instruction_locations=new_inst_locations
        )

    return filtered_program
