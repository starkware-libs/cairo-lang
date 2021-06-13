import dataclasses
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple

from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.preprocessor import PreprocessedProgram
from starkware.cairo.lang.compiler.scoped_name import ScopedName


@dataclasses.dataclass
class PassManagerContext:
    # A list of pairs (code, filename).
    codes: List[Tuple[str, str]]
    main_scope: ScopedName
    identifiers: IdentifierManager
    modules: List[CairoModule] = dataclasses.field(default_factory=list)
    identifier_locations: Dict[ScopedName, Location] = dataclasses.field(default_factory=dict)
    preprocessed_program: Optional[PreprocessedProgram] = None
    # A set of functions to compile (None means all functions will be compiled).
    # If the unused function optimization is enabled, only reachable functions will be compiled.
    functions_to_compile: Optional[Set[ScopedName]] = None


class Stage(ABC):
    """
    Represents a compilation stage.
    """

    @abstractmethod
    def run(self, context: PassManagerContext):
        """
        Runs the stage on the given context. The stage may modify context.
        """


class PassManager:
    """
    Manages the preprocessor's stages.
    """

    def __init__(self):
        # The list of stages.
        self.stages: List[Tuple[str, Stage]] = []
        # A set of stage names.
        self.stage_names: Set[str] = set()

    def run(self, context: PassManagerContext):
        for _, stage in self.stages:
            stage.run(context)

    def get_stage_index(self, name: str):
        assert name in self.stage_names
        index, = [i for i, (stage_name, _) in enumerate(self.stages) if stage_name == name]
        return index

    # Functions for manipulating the stages:

    def add_stage(self, new_stage_name: str, new_stage: Stage, index: Optional[int] = None):
        """
        Adds a stage at the end.
        """
        assert new_stage_name not in self.stage_names
        if index is None:
            index = len(self.stages)
        self.stages.insert(index, (new_stage_name, new_stage))
        self.stage_names.add(new_stage_name)

    def add_before(self, existing_stage: str, new_stage_name: str, new_stage: Stage):
        """
        Adds a new stage before 'existing_stage'.
        """
        self.add_stage(new_stage_name, new_stage, index=self.get_stage_index(existing_stage))

    def add_after(self, existing_stage: str, new_stage_name: str, new_stage: Stage):
        """
        Adds a new stage after 'existing_stage'.
        """
        self.add_stage(new_stage_name, new_stage, index=self.get_stage_index(existing_stage) + 1)

    def replace(self, existing_stage: str, new_stage: Stage):
        """
        Replaces 'existing_stage' with the given stage.
        """
        self.stages[self.get_stage_index(existing_stage)] = (existing_stage, new_stage)


class VisitorStage(Stage):
    """
    A generic stage that runs a visitor on the AST.
    """

    def __init__(self, visitor_factory, modify_ast=False):
        self.visitor_factory = visitor_factory
        self.modify_ast = modify_ast

    def run(self, context: PassManagerContext):
        visitor = self.visitor_factory(context)
        modified_modules = []
        for module in context.modules:
            modified_modules.append(visitor.visit(module))
        if self.modify_ast:
            context.modules = modified_modules
