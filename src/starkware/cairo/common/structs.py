from typing import List, MutableMapping, NamedTuple, Optional

from starkware.cairo.lang.compiler.ast.code_elements import CodeElementFunction
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.python.utils import WriteOnceDict


class CairoStructFactory:
    def __init__(
        self,
        identifiers: IdentifierManager,
        main_scope: Optional[ScopedName] = None,
        additional_imports: Optional[List[str]] = None,
    ):
        """
        Creates a CairoStructFactory that converts Cairo structs to python namedtuples.

        identifiers - an identifier manager holding the structs.
        additional_imports - An optional list of fully qualified names of structs to preload.
          Useful for importing absolute paths, rather than relative.
        """
        self.identifiers = identifiers
        self.main_scopes = [main_scope] if main_scope is not None else []

        self.resolved_identifiers: MutableMapping[ScopedName, ScopedName] = WriteOnceDict()
        if additional_imports is not None:
            for identifier_path in additional_imports:
                scope_name = ScopedName.from_string(identifier_path)
                # Call get_struct_definition to make sure scope_name is a struct.
                get_struct_definition(struct_name=scope_name, identifier_manager=identifiers)
                self.resolved_identifiers[scope_name[-1:]] = scope_name

    @classmethod
    def from_program(cls, program: Program, additional_imports: Optional[List[str]] = None):
        return cls(
            identifiers=program.identifiers,
            additional_imports=additional_imports,
            main_scope=program.main_scope,
        )

    def _get_full_name(self, name: ScopedName):
        full_name = self.resolved_identifiers.get(name)
        if full_name is not None:
            return full_name

        return self.identifiers.search(
            accessible_scopes=[*self.main_scopes, ScopedName()], name=name
        ).get_canonical_name()

    def get_struct_definition(self, name: ScopedName) -> StructDefinition:
        """
        Returns the struct definition of the given struct.
        """
        full_name = self._get_full_name(name)
        return get_struct_definition(full_name, self.identifiers)

    def build_struct(self, name: ScopedName):
        """
        Builds and returns namedtuple from a Cairo struct.
        """
        struct_def = self.get_struct_definition(name=name)

        typed_fields = [
            (member_name, type(member_def.cairo_type))
            for member_name, member_def in struct_def.members.items()
        ]

        return NamedTuple(struct_def.full_name.path[-1], typed_fields)

    def build_func_args(self, func: ScopedName):
        """
        Builds a namedtuple that contains both the explicit and the implicit arguments of 'func'.
        """
        full_name = self._get_full_name(func)

        implict_args = get_struct_definition(
            full_name + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE, self.identifiers
        ).members
        args = get_struct_definition(
            full_name + CodeElementFunction.ARGUMENT_SCOPE, self.identifiers
        ).members

        typed_fields = [
            (member_name, type(member_def.cairo_type))
            for member_name, member_def in {**implict_args, **args}.items()
        ]

        return NamedTuple(f"{func[-1:]}_full_args", typed_fields)

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

    def __getattr__(self, name: str) -> "CairoStructProxy":
        return CairoStructProxy(self.factory, self.path + name)

    def build(self):
        return self.factory.build_struct(self.path)

    def __call__(self, *args, **kwargs):
        return self.build()(*args, **kwargs)

    @property
    def struct_definition_(self) -> StructDefinition:
        return self.factory.get_struct_definition(self.path)

    @property
    def size(self):
        return self.struct_definition_.size

    def from_ptr(self, memory, addr):
        """
        Interprets addr as a pointer to a struct of type path and creates the corresponding
        namedtuple instance.
        """
        named_tuple = self.build()

        return named_tuple(
            **{name: memory[addr + index] for index, name in enumerate(named_tuple._fields)}
        )
