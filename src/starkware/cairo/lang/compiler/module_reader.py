import os
from typing import Callable, List, Set, Tuple

from starkware.cairo.lang.compiler.scoped_name import ScopedName


class ModuleReader:
    """
    Utility used to read module files based on the module names.
    The module files must be under the one of the directories in paths, and end with cairo_suffix.
    The file path is resolved by the order of paths.

    For example, if the paths is ['/usr/include', '/home/alice'] and the cairo_suffix is 'cairo'
    the code of the module 'foo.bar' is expected to be at
    '/usr/include/foo/bar.cairo' or '/home/alice/foo/bar.cairo', and taken from the first option
    if possible.
    """

    def __init__(self, paths: List[str], cairo_suffix: str):
        self.paths: List[str] = paths
        self.cairo_suffix: str = cairo_suffix
        self.source_files_with_scopes: Set[Tuple[str, str]] = set()

    @property
    def source_files(self):
        return set(filename for filename, scope in self.source_files_with_scopes)

    def module_to_file_path(
            self, module_name: str, isfile: Callable[[str], bool] = os.path.isfile) -> str:
        """
        Translates module name to file path.
        """
        # Extract the path, add to it the root directory path.
        path = list(ScopedName.from_string(module_name).path)
        # Add the cairo file suffix.
        path[-1] += self.cairo_suffix

        # Search for the file in the provided paths.
        # Keep records of tested paths, used to present indicative error if file not found.
        checked_filenames = []
        for directory in self.paths:
            filename = os.path.join(directory, *path)
            checked_filenames.append(filename)
            if isfile(filename):
                return filename

        # File not found.
        raise ModuleNotFoundException(module=module_name, paths=checked_filenames)

    def read(self, module_name: str) -> Tuple[str, str]:
        """
        Given a module name, translates it to a file path to read
        the module from, and returns the module code and filename.
        """
        filename = self.module_to_file_path(module_name)
        self.source_files.add(filename)
        self.source_files_with_scopes.add((filename, ScopedName.from_string(module_name)))
        with open(filename, 'r') as f:
            return f.read(), filename


class ModuleNotFoundException(Exception):
    def __init__(self, module: str, paths: List[str]):
        msg = f"Could not find module '{module}'. Searched in the following paths:"
        for path in paths:
            msg += '\n' + path
        super().__init__(msg)
