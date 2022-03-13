import dataclasses
from abc import ABC, abstractmethod
from typing import Any, Callable, List, MutableMapping, Optional, Union

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    TypeFelt,
    TypePointer,
    TypeStruct,
)
from starkware.cairo.lang.compiler.ast.expr import ExprCast, ExprDeref, Expression
from starkware.cairo.lang.compiler.constants import SIZE_CONSTANT
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition,
    IdentifierDefinition,
    LabelDefinition,
    NamespaceDefinition,
    ReferenceDefinition,
    StructDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierError,
    IdentifierManager,
    IdentifierScope,
    IdentifierSearchResult,
    MissingIdentifierError,
)
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingData, ReferenceManager
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable


@dataclasses.dataclass
class VmConstsContext:
    identifiers: IdentifierManager
    evaluator: Callable[[Expression], Any]
    reference_manager: ReferenceManager
    flow_tracking_data: FlowTrackingData
    memory: MutableMapping[MaybeRelocatable, MaybeRelocatable]
    pc: int


class VmConstsBase(ABC):
    """
    Represents constants and scopes accessible by hints.
    An instance returns a new instance of VmConstsBase when an attribute representing a subscope
    is accessed (the name of the scope is the name of the attribute).
    When an attribute having a name of a constant is accessed, the constant value is returned.
    """

    def __init__(self, context: VmConstsContext):
        object.__setattr__(self, "_context", context)

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        try:
            return self.get_or_set_value(name, None)
        except FlowTrackingError:
            raise FlowTrackingError(f"Reference '{name}' is revoked.") from None

    def __setattr__(self, name: str, value):
        assert value is not None, "Setting a value to None is not allowed."
        try:
            self.get_or_set_value(name, value)
        except FlowTrackingError:
            raise FlowTrackingError(f"Reference '{name}' is revoked.") from None

    @abstractmethod
    def get_or_set_value(self, name: str, set_value: Optional[MaybeRelocatable]):
        """
        If set_value is None, returns the value of the given attribute. Otherwise, sets it to
        set_value (setting to None will not work).
        """


def search_identifier_or_scope(
    identifiers: IdentifierManager, accessible_scopes: List[ScopedName], name: ScopedName
) -> Union[IdentifierSearchResult, "IdentifierScope"]:
    """
    If there is an identifier with the given name, returns an IdentifierSearchResult.
    Otherwise, if there is a scope with that name, returns the IdentifierScope instance.
    If name does not refer to an identifier or a scope, raises an exception.
    """
    try:
        return identifiers.search(accessible_scopes=accessible_scopes, name=name)
    except IdentifierError as exc:
        first_exception = exc

    try:
        return identifiers.search_scope(accessible_scopes=accessible_scopes, name=name)
    except IdentifierError:
        raise first_exception from None


class VmConsts(VmConstsBase):
    def __init__(
        self,
        *,
        accessible_scopes: List[ScopedName],
        path: ScopedName = ScopedName(),
        instruction_offset: Optional[int] = None,
        **kw,
    ):
        """
        Constructs a VmConsts which is used to dynamically resolve constant values.
        The 'path' parameter is the scoped name used to get from the global consts variable
        to the current VmConsts.
        The path is used only to throw errors in case of a non accessible identifier,
        the error for non accessible identifier 'a' would indicate <path>.a is non accessible.
        instruction_offset is an optional offset relative to the start of the program. If there
        is a label with the name 'path' then it holds the offset of said label.
        """
        super().__init__(**kw)
        object.__setattr__(self, "_accessible_scopes", accessible_scopes)
        object.__setattr__(self, "_path", path)
        if instruction_offset is not None:
            object.__setattr__(self, "instruction_offset_", instruction_offset)

    def get_or_set_value(self, name: str, set_value: Optional[MaybeRelocatable]):
        """
        If set_value is None, returns the value of the given attribute. Otherwise, sets it to
        set_value (setting to None will not work).
        """
        try:
            # Handle attributes representing program scopes and constants.
            result = search_identifier_or_scope(
                identifiers=self._context.identifiers,
                accessible_scopes=self._accessible_scopes,
                name=ScopedName.from_string(name),
            )
        except MissingIdentifierError as exc:
            raise MissingIdentifierError(self._path + exc.fullname) from None

        value: Optional[IdentifierDefinition]
        if isinstance(result, IdentifierSearchResult):
            value = result.identifier_definition
            handler_name = f"handle_{type(value).__name__}"
            scope = result.get_canonical_name()
            identifier_type = value.TYPE
        elif isinstance(result, IdentifierScope):
            value = None
            handler_name = "handle_scope"
            scope = result.fullname
            identifier_type = "scope"
        else:
            raise NotImplementedError(f"Unexpected type {type(result).__name__}.")

        if handler_name not in dir(self):
            self.raise_unsupported_error(name=self._path + name, identifier_type=identifier_type)

        return getattr(self, handler_name)(name, value, scope, set_value)

    def handle_ConstDefinition(
        self,
        name: str,
        identifier: ConstDefinition,
        scope: ScopedName,
        set_value: Optional[MaybeRelocatable],
    ):
        assert set_value is None, "Cannot change the value of a constant."
        # The current attribute is a const, return its value.
        return identifier.value

    def handle_scope(
        self,
        name: str,
        identifier: Union[IdentifierScope, LabelDefinition, NamespaceDefinition],
        scope: ScopedName,
        set_value: Optional[MaybeRelocatable],
    ):
        assert set_value is None, "Cannot change the value of a scope definition."
        # The current attribute is a namespace or a label.
        return VmConsts(
            context=self._context,
            accessible_scopes=[scope],
            path=self._path + name,
            instruction_offset=identifier.pc if isinstance(identifier, LabelDefinition) else None,
        )

    handle_LabelDefinition = handle_scope
    handle_NamespaceDefinition = handle_scope
    handle_FunctionDefinition = handle_scope

    def handle_StructDefinition(
        self,
        name: str,
        identifier: StructDefinition,
        scope: ScopedName,
        set_value: Optional[MaybeRelocatable],
    ):
        assert set_value is None, "Cannot change the value of a struct definition."

        return VmConstsStruct(
            context=self._context,
            struct_definition=identifier,
        )

    def handle_ReferenceDefinition(
        self,
        name: str,
        identifier: ReferenceDefinition,
        scope: ScopedName,
        set_value: Optional[MaybeRelocatable],
    ):
        # In set mode, take the address of the given reference instead.
        reference = self._context.flow_tracking_data.resolve_reference(
            reference_manager=self._context.reference_manager, name=identifier.full_name
        )

        if set_value is None:
            expr = reference.eval(self._context.flow_tracking_data.ap_tracking)
            expr, expr_type = simplify_type_system(expr, identifiers=self._context.identifiers)
            if isinstance(expr_type, TypeStruct):
                # If the reference is of type T, take its address and treat it as T*.
                assert isinstance(
                    expr, ExprDeref
                ), f"Expected expression of type '{expr_type.format()}' to have an address."
                expr = expr.addr
                expr_type = TypePointer(pointee=expr_type)
            val = self._context.evaluator(expr)

            # Check if the type is felt* or any_type**.
            if is_simple_type(expr_type):
                return val
            else:
                # Typed reference, return VmConstsReference which allows accessing members.
                assert isinstance(expr_type, TypePointer) and isinstance(
                    expr_type.pointee, TypeStruct
                ), "Type must be of the form T*."
                return VmConstsReference(
                    context=self._context, struct_name=expr_type.pointee.scope, reference_value=val
                )
        else:
            assert str(scope[-1:]) == name, "Expecting scope to end with name."
            value, value_type = simplify_type_system(
                reference.value, identifiers=self._context.identifiers
            )
            assert isinstance(
                value, ExprDeref
            ), f"""\
{scope} (= {value.format()}) does not reference memory and cannot be assigned."""

            value_ref = Reference(
                pc=reference.pc,
                value=ExprCast(expr=value.addr, dest_type=value_type),
                ap_tracking_data=reference.ap_tracking_data,
            )

            addr = self._context.evaluator(
                value_ref.eval(self._context.flow_tracking_data.ap_tracking)
            )
            self._context.memory[addr] = set_value

    def raise_unsupported_error(self, name: ScopedName, identifier_type: str):
        """
        Raises an exception which says that the identifier type is not supported.
        """
        raise NotImplementedError(
            f"Unsupported identifier type '{identifier_type}' of identifier '{name}'."
        )


class VmConstsReference(VmConstsBase):
    def __init__(self, *, reference_value, struct_name: ScopedName, **kw):
        """
        Constructs a VmConstsReference which allows accessing a typed reference fields.
        """
        super().__init__(**kw)

        object.__setattr__(
            self,
            "_struct_definition",
            get_struct_definition(
                struct_name=struct_name, identifier_manager=self._context.identifiers
            ),
        )

        object.__setattr__(self, "_reference_value", reference_value)
        object.__setattr__(self, "address_", reference_value)

    @property
    def type_(self):
        return VmConstsStruct(
            context=self._context,
            struct_definition=self._struct_definition,
        )

    def get_or_set_value(self, name: str, set_value: Optional[MaybeRelocatable]):
        """
        If set_value is None, returns the value of the given attribute. Otherwise, sets it to
        set_value (setting to None will not work).
        """

        member_def = self._struct_definition.members.get(name)
        if member_def is None:
            raise IdentifierError(
                f"'{name}' is not a member of '{self._struct_definition.full_name}'."
            ) from None

        addr = self._reference_value + member_def.offset

        if set_value is not None:
            self._context.memory[addr] = set_value
        else:
            expr_type = member_def.cairo_type
            if is_simple_type(expr_type):
                return self._context.memory[addr]
            elif isinstance(expr_type, TypeStruct):
                return VmConstsReference(
                    context=self._context, struct_name=expr_type.scope, reference_value=addr
                )
            else:
                # Typed reference, return VmConstsReference which allows accessing members.
                assert isinstance(expr_type, TypePointer) and isinstance(
                    expr_type.pointee, TypeStruct
                ), "Type must be of the form T*."
                return VmConstsReference(
                    context=self._context,
                    struct_name=expr_type.pointee.scope,
                    reference_value=self._context.memory[addr],
                )


def is_simple_type(expr_type: CairoType) -> bool:
    """
    Returns True if the type is felt, felt*, T**, T***, ... (in particular, returns False if the
    type is T or T*). When you access a value whose type is one of the above (e.g., ids.x),
    the returned value will be a int/relocatable value (unlike T and T* where the returned value
    is VmConstsReference to allow accessing submembers).
    """
    is_pointer_to_felt_or_pointer = isinstance(expr_type, TypePointer) and isinstance(
        expr_type.pointee, (TypePointer, TypeFelt)
    )
    return isinstance(expr_type, TypeFelt) or is_pointer_to_felt_or_pointer


class VmConstsStruct(VmConstsBase):
    def __init__(self, *, struct_definition: StructDefinition, **kw):
        """
        Constructs a VmConstsStruct which allows accessing structs.
        """
        super().__init__(**kw)
        object.__setattr__(self, "_struct_definition", struct_definition)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return (
            self._struct_definition == other._struct_definition and self._context is other._context
        )

    def get_or_set_value(self, name: str, set_value: Optional[MaybeRelocatable]):
        assert set_value is None, "Cannot change the value of a constant."

        if name == str(SIZE_CONSTANT):
            return self._struct_definition.size

        member_def = self._struct_definition.members.get(name)
        if member_def is None:
            raise IdentifierError(
                f"'{name}' is not a member of '{self._struct_definition.full_name}'."
            ) from None

        return member_def.offset
