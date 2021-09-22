from typing import Callable, Dict, List, Optional, Tuple

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock,
    CodeElement,
    CodeElementFunction,
    CodeElementImport,
)
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.ast.visitor import Visitor, get_lang_from_file
from starkware.cairo.lang.compiler.error_handling import Location, LocationError
from starkware.cairo.lang.compiler.module_reader import ModuleNotFoundException
from starkware.cairo.lang.compiler.parser import parse_file


def collect_imports(
    curr_pkg_name: str, read_file: Callable[[str], Tuple[str, str]]
) -> Dict[str, CairoFile]:
    """
    Scans the graph of file imports (using DFS), starting with curr_pkg_name,
    and returns an ordered dictionary mapping package names to CairoFile AST.
    The returned dictionary is topologically ordered, such that every package
    depends only on prior packages.
    'read_file' is a strategy to access code files. Given a package name
    (as written in the using directive) it returns a pair (file content, file name).
    curr_pkg_name must be provided in the same format.
    """

    collector = ImportsCollector(read_file)
    collector.collect(curr_pkg_name)
    return collector.collected_data


class UsingCycleError(Exception):
    """
    Represents an error thrown when a cyclic dependency is found.
    """

    def __init__(self, cycle: List[str]):
        super().__init__(f"Found circular imports dependency:\n{self.cycle_to_string(cycle)}")
        self.cycle = cycle

    @staticmethod
    def cycle_to_string(cycle):
        res = ""
        for v in cycle[:-1]:
            res += f"{v} imports\n"
        res += cycle[-1]
        return res


class ImportLoaderError(LocationError):
    pass


class ImportsCollector:
    def __init__(self, read_file: Callable[[str], Tuple[str, str]]):
        self.curr_ancestors: List[str] = []
        self.collected_data: Dict[str, CairoFile] = {}
        self.lang: Dict[str, Optional[str]] = {}
        self.read_file = read_file

    def collect(self, curr_pkg_name: str, location: Optional[Location] = None):
        # Check for circular dependencies.
        if curr_pkg_name in self.curr_ancestors:
            raise UsingCycleError(self.curr_ancestors + [curr_pkg_name])

        if curr_pkg_name in self.collected_data:
            # File already parsed.
            return

        try:
            code, filename = self.read_file(curr_pkg_name)
        except ModuleNotFoundException as e:
            raise ImportLoaderError(str(e), location=location)
        except Exception as e:
            raise ImportLoaderError(
                f"Could not load module '{curr_pkg_name}'.\nError: {e}", location=location
            )

        parsed_file: CairoFile = parse_file(code, filename=filename)

        lang = get_lang_from_file(parsed_file)

        # Get current file dependencies.
        collector = DirectDependenciesCollector()
        collector.get_using_pkgs_in_block(parsed_file.code_block)

        # Add current package to ancestors list before scanning its dependencies.
        self.curr_ancestors.append(curr_pkg_name)

        # Collect ASTs recursively.
        for pkg_name, location in collector.packages:
            self.collect(pkg_name, location=location)
            if not (self.lang[pkg_name] is None or self.lang[pkg_name] == lang):
                raise ImportLoaderError(
                    f"Importing modules with %lang directive '{self.lang[pkg_name]}' must "
                    "be from a module with the same directive.",
                    location=location,
                )

        # Pop current package from ancestors list after scanning its dependencies.
        self.curr_ancestors.pop()
        self.collected_data[curr_pkg_name] = parsed_file
        self.lang[curr_pkg_name] = lang


class DirectDependenciesCollector(Visitor):
    """
    Collects module names used in a code element.
    Uses the visitor design pattern.
    """

    def __init__(self):
        super().__init__()
        # List of pairs (pkg name, using location in file).
        self.packages: List[Tuple[str, Optional[Location]]] = []

    def get_using_pkgs_in_block(self, code_block: CodeBlock):
        """
        Visits imported package names in the CodeBlock.
        """
        for elm in code_block.code_elements:
            self.visit(elm.code_elm)

    def _visit_default(self, obj):
        assert isinstance(obj, CodeElement), f"Got unexpected type {type(obj).__name__}."

    def visit_CodeBlock(self, elm: CodeBlock):
        pass

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        self.get_using_pkgs_in_block(elm.code_block)

    def visit_CodeElementImport(self, elm: CodeElementImport):
        self.packages.append((elm.path.name, elm.path.location))
