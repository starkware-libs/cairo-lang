import dataclasses
from typing import Any, Callable, List, Optional, Union

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.ast.expr import ExprCast, ExprDeref, Expression
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition, IdentifierDefinition, LabelDefinition, MemberDefinition, ReferenceDefinition)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierError, IdentifierManager, IdentifierScope, IdentifierSearchResult,
    MissingIdentifierError)
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingData, ReferenceManager
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable


@dataclasses.dataclass
class VmConstsContext:
    identifiers: IdentifierManager
    evaluator: Callable[[Expression], Any]
    reference_manager: ReferenceManager
    flow_tracking_data: FlowTrackingData
    memory: MemoryDict
    pc: int


class VmConstsBase:
    """
    Represents constants and scopes accessible by hints.
    An instance returns a new instance of VmConstsBase when an attribute representing a subscope
    is accessed (the name of the scope is the name of the attribute).
    When an attribute having a name of a constant is accessed, the constant value is returned.
    """

    def __init__(
            self, context: VmConstsContext, accessible_scopes: List[ScopedName],
            path: ScopedName = ScopedName()):
        """
        Constructs a VmConstsBase object used to dynamically resolve constant values.
        The 'path' parameter is the scoped name used to get from the global consts variable
        to the current VmConstsBase.
        The path is used only to throw errors in case of a non accessible identifier,
        the error for non accessible identifier 'a' would indicate <path>.a is non accessible.
        """
        object.__setattr__(self, '_context', context)
        object.__setattr__(self, '_accessible_scopes', accessible_scopes)
        object.__setattr__(self, '_path', path)

    def __getattr__(self, name: str):
        if name.startswith('__'):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'")
        return self.get_or_set_value(name, None)

    def __setattr__(self, name: str, value):
        assert value is not None, 'Setting a value to None is not allowed.'
        self.get_or_set_value(name, value)

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
                name=ScopedName.from_string(name))
        except MissingIdentifierError as exc:
            raise MissingIdentifierError(self._path + exc.fullname) from None

        value: Optional[IdentifierDefinition]
        if isinstance(result, IdentifierSearchResult):
            value = result.identifier_definition
            handler_name = f'handle_{type(value).__name__}'
            scope = result.canonical_name
            identifier_type = value.TYPE
        elif isinstance(result, IdentifierScope):
            value = None
            handler_name = 'handle_scope'
            scope = result.fullname
            identifier_type = 'scope'
        else:
            raise NotImplementedError(f'Unexpected type {type(result).__name__}.')

        if handler_name not in dir(self):
            self.raise_unsupported_error(name=self._path + name, identifier_type=identifier_type)

        return getattr(self, handler_name)(name, value, scope, set_value)

    def raise_unsupported_error(self, name: ScopedName, identifier_type: str):
        """
        Raises an exception which says that the identifier type is not supported.
        This method can be overridden by subclasses.
        """
        raise NotImplementedError(
            f"Unsupported identifier type '{identifier_type}' of identifier '{name}'.")


def search_identifier_or_scope(
        identifiers: IdentifierManager, accessible_scopes: List[ScopedName],
        name: ScopedName) -> Union[IdentifierSearchResult, 'IdentifierScope']:
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
    def handle_ConstDefinition(
            self, name: str, identifier: ConstDefinition, scope: ScopedName,
            set_value: Optional[MaybeRelocatable]):
        assert set_value is None, 'Cannot change the value of a constant.'
        # The current attribute is a const, return its value.
        return identifier.value

    def handle_MemberDefinition(
            self, name: str, identifier: MemberDefinition, scope: ScopedName,
            set_value: Optional[MaybeRelocatable]):
        assert set_value is None, 'Cannot change the value of a member offset.'
        # The current attribute is a const, return its value.
        return identifier.offset

    def handle_scope(
            self, name: str, identifier: Union[IdentifierScope, LabelDefinition],
            scope: ScopedName, set_value: Optional[MaybeRelocatable]):
        assert set_value is None, 'Cannot change the value of a scope definition.'
        # The current attribute is a namespace or a label.
        return VmConsts(
            context=self._context,
            accessible_scopes=[scope],
            path=self._path + name)

    handle_LabelDefinition = handle_scope

    def handle_ReferenceDefinition(
            self, name: str, identifier: ReferenceDefinition, scope: ScopedName,
            set_value: Optional[MaybeRelocatable]):
        # In set mode, take the address of the given reference instead.
        reference = self._context.flow_tracking_data.resolve_reference(
            reference_manager=self._context.reference_manager, name=identifier.full_name)

        if set_value is None:
            expr = reference.eval(
                self._context.flow_tracking_data.ap_tracking)
            expr, expr_type = simplify_type_system(expr)
            if isinstance(expr_type, TypeStruct):
                # If the reference is of type T, take its address and treat it as T*.
                assert isinstance(expr, ExprDeref), \
                    f"Expected expression of type '{expr_type.format()}' to have an address."
                expr = expr.addr
                expr_type = TypePointer(pointee=expr_type)
            val = self._context.evaluator(expr)

            # Check if the type is felt* or any_type**.
            is_pointer_to_felt_or_pointer = (
                isinstance(expr_type, TypePointer) and
                isinstance(expr_type.pointee, (TypePointer, TypeFelt)))
            if isinstance(expr_type, TypeFelt) or is_pointer_to_felt_or_pointer:
                return val
            else:
                # Typed reference, return VmConstsReference which allows accessing members.
                assert isinstance(expr_type, TypePointer) and \
                    isinstance(expr_type.pointee, TypeStruct), \
                    'Type must be of the form T*.'
                return VmConstsReference(
                    context=self._context,
                    accessible_scopes=[expr_type.pointee.scope],
                    reference_value=val,
                    add_addr_var=True)
        else:
            assert str(scope[-1:]) == name, 'Expecting scope to end with name.'
            value, value_type = simplify_type_system(reference.value)
            assert isinstance(value, ExprDeref), f"""\
{scope} (= {value.format()}) does not reference memory and cannot be assigned."""

            value_ref = Reference(
                pc=reference.pc,
                value=ExprCast(expr=value.addr, dest_type=value_type),
                ap_tracking_data=reference.ap_tracking_data,
            )

            addr = self._context.evaluator(value_ref.eval(
                self._context.flow_tracking_data.ap_tracking))
            self._context.memory[addr] = set_value


class VmConstsReference(VmConstsBase):
    def __init__(self, *, reference_value, add_addr_var: bool, **kw):
        """
        Constructs a VmConstsReference which allows accessing a typed reference fields.
        If add_addr_var, the value of the reference itself can be accessed using self.address_.
        """
        super().__init__(**kw)
        object.__setattr__(self, '_reference_value', reference_value)
        if add_addr_var:
            object.__setattr__(self, 'address_', reference_value)

    def handle_MemberDefinition(
            self, name, identifier: MemberDefinition, scope: ScopedName,
            set_value: Optional[MaybeRelocatable]):
        addr = self._reference_value + identifier.offset
        if set_value is not None:
            self._context.memory[addr] = set_value
        else:
            return self._context.memory[addr]

    def raise_unsupported_error(self, name: ScopedName, identifier_type: str):
        raise NotImplementedError(
            f"Expected a member, found '{name}' which is '{identifier_type}'.")
