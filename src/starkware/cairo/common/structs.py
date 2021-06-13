from collections import namedtuple
from typing import List, MutableMapping, Optional

from starkware.cairo.lang.compiler.ast.code_elements import CodeElementFunction
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.python.utils import WriteOnceDict


class CairoStructFactory:
    def __init__(
            self, identifiers: IdentifierManager, additional_imports: Optional[List[str]] = None):
        """
        Creates a CairoStructFactory that converts Cairo structs to python namedtuples.

        identifiers - an identifier manager holding the structs.
        additional_imports - An optional list of fully qualified names of structs to preload.
          Useful for importing absolute paths, rather than relative.
        """
        self.identifiers = identifiers

        self.resolved_identifiers: MutableMapping[ScopedName, ScopedName] = WriteOnceDict()
        if additional_imports is not None:
            for identifier_path in additional_imports:
                scope_name = ScopedName.from_string(identifier_path)
                # Call get_struct_definition to make sure scope_name is a struct.
                get_struct_definition(
                    struct_name=scope_name,
                    identifier_manager=identifiers)
                self.resolved_identifiers[scope_name[-1:]] = scope_name

    @classmethod
    def from_program(cls, program: Program, additional_imports: Optional[List[str]] = None):
        return cls(identifiers=program.identifiers, additional_imports=additional_imports)

    def _get_full_name(self, name: ScopedName):
        full_name = self.resolved_identifiers.get(name)
        if full_name is not None:
            return full_name

        return self.identifiers.search(
            accessible_scopes=[ScopedName.from_string('__main__'), ScopedName()],
            name=name).get_canonical_name()

    def build_struct(self, name: ScopedName):
        """
        Builds and returns namedtuple from a Cairo struct.
        """
        full_name = self._get_full_name(name)
        members = get_struct_definition(full_name, self.identifiers).members
        return namedtuple(full_name.path[-1], list(members.keys()))

    def get_struct_size(self, name: ScopedName) -> int:
        """
        Returns the size of the given struct.
        """
        full_name = self._get_full_name(name)
        return get_struct_definition(full_name, self.identifiers).size

    def build_func_args(self, func: ScopedName):
        """
        Builds a namedtuple that contains both the explicit and the implicit arguments of 'func'.
        """
        full_name = self._get_full_name(func)

        implict_args = get_struct_definition(
            full_name + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            self.identifiers).members
        args = get_struct_definition(
            full_name + CodeElementFunction.ARGUMENT_SCOPE, self.identifiers).members
        return namedtuple(f'{func[-1:]}_full_args', list({**implict_args, **args}))

    @property
    def structs(self):
        """
        Dynamic namespace of all available structs. For example, to get the namedtuple of
        a.b.MyStruct, use cairo_struct_factory.struct.a.b.MyStruct.
        """
        return CairoStructProxy(self, ScopedName())


class CairoStructProxy:
    """
    Helper class for CairoStructFactory. See CairoStructFactory.structs.
    """

    def __init__(self, factory: CairoStructFactory, path: ScopedName):
        self.factory = factory
        self.path = path

    def __getattr__(self, name: str) -> 'CairoStructProxy':
        return CairoStructProxy(self.factory, self.path + name)

    def build(self):
        return self.factory.build_struct(self.path)

    def __call__(self, *args, **kwargs):
        return self.build()(*args, **kwargs)

    @property
    def size(self):
        return self.factory.get_struct_size(self.path)

    def from_ptr(self, runner, addr):
        """
        Interprets addr as a pointer to a struct of type path and creates the corresponding
        namedtuple instance.
        """
        named_tuple = self.build()

        return named_tuple(**{
            name: runner.vm_memory[addr + index]
            for index, name in enumerate(named_tuple._fields)})
