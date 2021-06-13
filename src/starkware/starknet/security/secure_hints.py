from dataclasses import field
from typing import ClassVar, Dict, List, Set, Type

import marshmallow
import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.cairo.lang.compiler.preprocessor.flow import ReferenceManager
from starkware.cairo.lang.compiler.program import CairoHint, Program


class SetField(mfields.List):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        res = super()._serialize(value, attr, obj, **kwargs)
        return sorted(res, key=lambda x: (x['name'], x['expr']))

    def _deserialize(self, *args, **kwargs):
        return set(super()._deserialize(*args, **kwargs))


class InsecureHintError(Exception):
    pass


@marshmallow_dataclass.dataclass(frozen=True)
class NamedExpression:
    name: str
    expr: str

    def __lt__(self, other):
        if not isinstance(other, NamedExpression):
            return NotImplemented
        return (self.name, self.expr) < (other.name, other.expr)

    Schema: ClassVar[marshmallow.Schema]


@marshmallow_dataclass.dataclass
class HintsWhitelistEntry:
    hint_lines: List[str]
    allowed_expressions: Set[NamedExpression] = field(
        metadata=dict(marshmallow_field=SetField(mfields.Nested(NamedExpression.Schema))))

    Schema: ClassVar[Type[marshmallow.Schema]]

    def serialize(self) -> dict:
        return HintsWhitelistEntry.Schema().dump(self)


class HintsWhitelistDict(mfields.Field):
    """
    A field that behaves like a dictionary from hint to a set of allowed expressions, but
    serializes as a list where the hint is split to lines.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        return [
            HintsWhitelistEntry(
                hint_lines.split('\n'), allowed_expressions=allowed_expressions).serialize()
            for hint_lines, allowed_expressions in sorted(value.items())]

    def _deserialize(self, value, attr, data, **kwargs) -> Dict[str, Set[NamedExpression]]:
        entries = [HintsWhitelistEntry.Schema().load(entry) for entry in value]
        return {'\n'.join(entry.hint_lines): entry.allowed_expressions for entry in entries}


@marshmallow_dataclass.dataclass
class HintsWhitelist:
    """
    Checks the security of hints in a Cairo program against a whitelist.
    """

    # Maps a hint string to the set of allowed expressions in its references.
    allowed_reference_expressions_for_hint: Dict[str, Set[NamedExpression]] = field(
        metadata=dict(marshmallow_field=HintsWhitelistDict()))
    Schema: ClassVar[Type[marshmallow.Schema]]

    # Serialization operations.
    @classmethod
    def from_file(cls, filename: str) -> 'HintsWhitelist':
        with open(filename, 'r') as fp:
            return cls.Schema().loads(fp.read())

    @classmethod
    def from_program(cls, program: Program) -> 'HintsWhitelist':
        """
        Creates a whitelist from all the hints in an existing program.
        """
        whitelist = cls(allowed_reference_expressions_for_hint={})
        for hint in program.hints.values():
            whitelist.add_hint_to_whitelist(hint, program.reference_manager)
        return whitelist

    def add_hint_to_whitelist(self, hint: CairoHint, reference_manager: ReferenceManager):
        self.allowed_reference_expressions_for_hint.setdefault(hint.code, set()).update(
            self._get_hint_reference_expressions(hint, reference_manager))

    # Reading operations.
    def verify_program_hint_secure(self, program: Program):
        """
        Determines whether a Cairo program is hint-secure. This happens when all the
        hints and their associated reference expressions exist within a given whitelist.
        """
        for hint in program.hints.values():
            self.verify_hint_secure(
                hint=hint, reference_manager=program.reference_manager)

    def verify_hint_secure(self, hint: CairoHint, reference_manager: ReferenceManager):
        allowed_expressions = self.allowed_reference_expressions_for_hint.get(hint.code)
        if allowed_expressions is None:
            raise InsecureHintError(f'Hint is not whitelisted:\n{hint.code}')

        expressions = self._get_hint_reference_expressions(hint, reference_manager)
        invalid_expressions = expressions - allowed_expressions
        if invalid_expressions:
            raise InsecureHintError(
                f'Forbidden expressions in hint "{hint.code}":\n{sorted(invalid_expressions)}')

    def _get_hint_reference_expressions(
            self, hint: CairoHint, reference_manager: ReferenceManager) -> \
            Set[NamedExpression]:
        ref_exprs: Set[NamedExpression] = set()
        for ref_name, ref_id in hint.flow_tracking_data.reference_ids.items():
            ref = reference_manager.get_ref(ref_id)
            ref_exprs.add(NamedExpression(name=str(ref_name), expr=ref.value.format()))
        return ref_exprs
