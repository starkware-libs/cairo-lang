from typing import Callable, Dict, Optional, Sequence, Tuple, Type

from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.import_loader import collect_imports
from starkware.cairo.lang.compiler.preprocessor.dependency_graph import DependencyGraphStage
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import IdentifierCollector
from starkware.cairo.lang.compiler.preprocessor.pass_manager import (
    PassManager, PassManagerContext, Stage, VisitorStage)
from starkware.cairo.lang.compiler.preprocessor.preprocessor import Preprocessor
from starkware.cairo.lang.compiler.preprocessor.struct_collector import StructCollector
from starkware.cairo.lang.compiler.preprocessor.unique_labels import UniqueLabelCreator
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def default_pass_manager(
        prime: int,
        read_module: Callable[[str], Tuple[str, str]],
        preprocessor_cls: Optional[Type[Preprocessor]] = None,
        opt_unused_functions: bool = True,
        preprocessor_kwargs: Optional[Dict] = None) -> PassManager:
    manager = PassManager()
    manager.add_stage('module_collector', ModuleCollector(read_module=read_module))
    manager.add_stage('unique_label_creator', VisitorStage(
        lambda context: UniqueLabelCreator(), modify_ast=True))
    manager.add_stage('identifier_collector', VisitorStage(
        lambda context: IdentifierCollector(identifiers=context.identifiers)))
    if opt_unused_functions:
        manager.add_stage('dependency_graph', DependencyGraphStage())
    manager.add_stage('struct_collector', VisitorStage(
        lambda context: StructCollector(identifiers=context.identifiers)))
    manager.add_stage('preprocessor', PreprocessorStage(
        prime, preprocessor_cls, preprocessor_kwargs))
    return manager


class PreprocessorStage(Stage):
    def __init__(
            self, prime: int, preprocessor_cls: Optional[Type[Preprocessor]] = None,
            preprocessor_kwargs: Optional[Dict] = None):
        self.prime = prime
        if preprocessor_cls is None:
            self.preprocessor_cls = Preprocessor
        else:
            self.preprocessor_cls = preprocessor_cls
        self.preprocessor_kwargs = {} if preprocessor_kwargs is None else preprocessor_kwargs

    def run(self, context: PassManagerContext):
        preprocessor = self.preprocessor_cls(
            prime=self.prime, identifiers=context.identifiers,
            functions_to_compile=context.functions_to_compile, **self.preprocessor_kwargs)
        preprocessor.identifier_locations = context.identifier_locations

        for module in context.modules:
            preprocessor.visit(module)

        preprocessor.resolve_labels()
        context.preprocessed_program = preprocessor.get_program()


class ModuleCollector(Stage):
    def __init__(
            self, read_module: Callable[[str], Tuple[str, str]],
            additional_modules: Optional[Sequence[str]] = None):
        self.read_module = read_module
        self.additional_modules = [] if additional_modules is None else list(additional_modules)

    def run(self, context: PassManagerContext):
        visited_modules = set()

        for additional_module in self.additional_modules:
            files = collect_imports(additional_module, read_file=self.read_module)
            for module_name, ast in files.items():
                if module_name in visited_modules:
                    continue
                visited_modules.add(module_name)
                scope = ScopedName.from_string(module_name)
                context.modules.append(CairoModule(cairo_file=ast, module_name=scope))

        for code, filename in context.codes:
            # Function used to read files given module names.
            # The root module (filename) is handled separately, for this module code is returned.
            def read_file_fixed(name):
                return (code, filename) if name == filename else self.read_module(name)

            files = collect_imports(filename, read_file=read_file_fixed)
            for module_name, ast in files.items():
                # Check if the module is one of the files given in 'context.codes'.
                is_main_scope = module_name == filename
                if is_main_scope:
                    scope = context.main_scope
                else:
                    scope = ScopedName.from_string(module_name)
                    if module_name in visited_modules:
                        continue
                    visited_modules.add(module_name)
                context.modules.append(CairoModule(cairo_file=ast, module_name=scope))
