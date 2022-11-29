import dataclasses
import re
from typing import List, Optional, Tuple

import lark
from lark import Token, Transformer, v_args

from starkware.cairo.lang.compiler.ast.aliased_identifier import AliasedIdentifier
from starkware.cairo.lang.compiler.ast.arguments import IdentifierList
from starkware.cairo.lang.compiler.ast.bool_expr import BoolAndExpr, BoolEqExpr, BoolExpr
from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    TypeCodeoffset,
    TypeFelt,
    TypeIdentifier,
    TypePointer,
    TypeStruct,
    TypeTuple,
)
from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective,
    CodeBlock,
    CodeElementAllocLocals,
    CodeElementCompoundAssertEq,
    CodeElementConst,
    CodeElementDirective,
    CodeElementEmptyLine,
    CodeElementFuncCall,
    CodeElementFunction,
    CodeElementHint,
    CodeElementIf,
    CodeElementImport,
    CodeElementInstruction,
    CodeElementLabel,
    CodeElementLocalVariable,
    CodeElementMember,
    CodeElementReference,
    CodeElementReturn,
    CodeElementReturnValueReference,
    CodeElementStaticAssert,
    CodeElementTailCall,
    CodeElementTemporaryVariable,
    CodeElementTypeDef,
    CodeElementUnpackBinding,
    CodeElementWith,
    CodeElementWithAttr,
    CommentedCodeElement,
    LangDirective,
)
from starkware.cairo.lang.compiler.ast.expr import (
    ArgList,
    ExprAddressOf,
    ExprAssignment,
    ExprCast,
    ExprConst,
    ExprDeref,
    ExprDot,
    Expression,
    ExprHint,
    ExprIdentifier,
    ExprNeg,
    ExprNewOperator,
    ExprOperator,
    ExprParentheses,
    ExprPow,
    ExprReg,
    ExprSubscript,
    ExprTuple,
)
from starkware.cairo.lang.compiler.ast.expr_func_call import ExprFuncCall
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction,
    AssertEqInstruction,
    CallInstruction,
    CallLabelInstruction,
    DefineWordInstruction,
    InstructionAst,
    JnzInstruction,
    JumpInstruction,
    JumpToLabelInstruction,
    RetInstruction,
)
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.ast.notes import Notes
from starkware.cairo.lang.compiler.ast.rvalue import (
    Rvalue,
    RvalueCall,
    RvalueCallInst,
    RvalueExpr,
    RvalueFuncCall,
)
from starkware.cairo.lang.compiler.ast.types import Modifier, TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import (
    InputFile,
    Location,
    LocationError,
    ParentLocation,
)
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.python.utils import as_non_optional

DEFAULT_SHORT_STRING_MAX_LENGTH = 31


@dataclasses.dataclass
class ParserContext:
    """
    Represents information that affects the parsing process.
    """

    short_string_max_length: int = DEFAULT_SHORT_STRING_MAX_LENGTH
    parent_location: Optional[ParentLocation] = None

    # If True, treat type identifiers as resolved.
    resolved_types: bool = False


class ParserError(LocationError):
    pass


@dataclasses.dataclass
class CommaSeparatedWithNotes:
    """
    Represents a list of comma separated values, such as expressions or types.
    """

    args: list
    notes: List[Notes]
    has_trailing_comma: bool


class ParserTransformer(Transformer):
    """
    Transforms the lark tree into an AST based on the classes defined in ast/*.py.
    """

    def __init__(self, input_file: InputFile, parser_context: Optional[ParserContext]):
        self.input_file = input_file
        self.parser_context = ParserContext() if parser_context is None else parser_context

    def __default__(self, data: str, children, meta):
        raise TypeError(f"Unable to parse tree node of type {data}")

    def comma_separated_with_notes(self, value) -> CommaSeparatedWithNotes:
        saw_comma = None
        all_notes: List[Notes] = []
        current_notes: List[Notes] = []
        args: list = []
        for v in value:
            if isinstance(v, Notes):
                # Join the notes before and after the comma.
                current_notes.append(v)
            elif isinstance(v, Token) and v.type == "COMMA":
                if saw_comma is not False:
                    raise ParserError("Unexpected comma.", location=self.token2loc(v))
                saw_comma = True
            else:
                if saw_comma is False:
                    raise ParserError(
                        "Expected a comma before this expression.", location=v.location
                    )
                all_notes.append(Notes.merge(current_notes))
                args.append(v)

                # Reset state.
                saw_comma = False
                current_notes = []

        all_notes.append(Notes.merge(current_notes))
        if saw_comma is None:
            saw_comma = False

        return CommaSeparatedWithNotes(
            args=args,
            notes=all_notes,
            has_trailing_comma=saw_comma,
        )

    # Types.

    @v_args(meta=True)
    def named_type(self, meta, value) -> TypeTuple.Item:
        name: Optional[str]
        if len(value) == 1:
            # Unnamed type.
            (typ,) = value
            name = None
            if isinstance(typ, ExprIdentifier):
                typ = self.type_struct([typ])
        elif len(value) == 2:
            # Named type.
            identifier, typ = value
            assert isinstance(identifier, ExprIdentifier)
            assert isinstance(typ, CairoType)
            if ScopedName.SEPARATOR in identifier.name:
                raise ParserError(
                    f"Unexpected '{ScopedName.SEPARATOR}' in name.", location=identifier.location
                )
            name = identifier.name
        else:
            raise NotImplementedError(f"Unexpected number of values. {value}")

        return TypeTuple.Item(name=name, typ=typ, location=self.meta2loc(meta))

    @v_args(meta=True)
    def type_felt(self, meta, value):
        return TypeFelt(location=self.meta2loc(meta))

    @v_args(meta=True)
    def type_codeoffset(self, meta, value):
        return TypeCodeoffset(location=self.meta2loc(meta))

    def type_struct(self, value):
        assert len(value) == 1 and isinstance(value[0], ExprIdentifier)
        if self.parser_context.resolved_types:
            # If parser_context.resolved_types is True, assume that the type is a struct.
            return TypeStruct(
                scope=ScopedName.from_string(value[0].name),
                location=value[0].location,
            )

        return TypeIdentifier(
            name=ScopedName.from_string(value[0].name),
            location=value[0].location,
        )

    @v_args(meta=True)
    def type_pointer(self, meta, value):
        return TypePointer(pointee=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def type_pointer2(self, meta, value):
        location = self.meta2loc(meta)
        inner_location = (
            None
            if location is None
            else dataclasses.replace(location, end_col=location.end_col - 1)
        )
        return TypePointer(
            pointee=TypePointer(pointee=value[0], location=inner_location), location=location
        )

    @v_args(meta=True)
    def type_tuple(self, meta, value: Tuple[CommaSeparatedWithNotes]):
        (lst,) = value
        return TypeTuple(
            members=lst.args,
            notes=lst.notes,
            has_trailing_comma=lst.has_trailing_comma,
            location=self.meta2loc(meta),
        )

    # Expression.
    @v_args(meta=True)
    def arg_list(self, meta, value: Tuple[CommaSeparatedWithNotes]):
        (lst,) = value
        return ArgList(
            args=lst.args,
            notes=lst.notes,
            has_trailing_comma=lst.has_trailing_comma,
            location=self.meta2loc(meta),
        )

    @v_args(meta=True)
    def expr_assignment(self, meta, value):
        if len(value) == 1:
            identifier = None
            expr = value[0]
        elif len(value) == 2:
            identifier, expr = value
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")
        return ExprAssignment(identifier=identifier, expr=expr, location=self.meta2loc(meta))

    @v_args(meta=True)
    def identifier(self, meta, value):
        return ExprIdentifier(name=".".join(x.value for x in value), location=self.meta2loc(meta))

    @v_args(meta=True)
    def identifier_def(self, meta, value):
        return ExprIdentifier(name=value[0].value, location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_number(self, meta, value):
        return ExprConst(val=int(value[0]), format_str=value[0].value, location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_hex_number(self, meta, value):
        return ExprConst(
            val=int(value[0], 16), format_str=value[0].value, location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def atom_short_string(self, meta, value):
        location = self.meta2loc(meta)
        token_text = value[0].value
        assert token_text[0] == token_text[-1] == "'"
        text = token_text[1:-1]
        max_length = self.parser_context.short_string_max_length
        if len(text) > max_length:
            raise ParserError(
                f"Short string (e.g., 'abc') length must be at most {max_length}.",
                location=location,
            )
        try:
            text_bytes = text.encode("ascii")
        except UnicodeEncodeError:
            raise ParserError(f"Expected an ascii string. Found: {repr(text)}.", location=location)

        text_bytes = backslash_to_hex(text_bytes)
        return ExprConst(
            val=int.from_bytes(text_bytes, "big"),
            format_str=token_text,
            location=location,
        )

    @v_args(meta=True)
    def atom_hint(self, meta, value):
        return ExprHint.from_str(val=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_reg(self, meta, value):
        return ExprReg(reg=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_func_call(self, meta, value):
        return ExprFuncCall(rvalue=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def expr_add(self, meta, value):
        return ExprOperator(
            a=value[0], op="+", b=value[2], notes=value[1], location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def expr_sub(self, meta, value):
        return ExprOperator(
            a=value[0], op="-", b=value[2], notes=value[1], location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def expr_mul(self, meta, value):
        return ExprOperator(
            a=value[0], op="*", b=value[2], notes=value[1], location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def expr_div(self, meta, value):
        return ExprOperator(
            a=value[0], op="/", b=value[2], notes=value[1], location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def unary_addressof(self, meta, value):
        return ExprAddressOf(expr=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def unary_neg(self, meta, value):
        return ExprNeg(val=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def unary_new_operator(self, meta, value):
        return ExprNewOperator(expr=value[0], is_typed=True, location=self.meta2loc(meta))

    @v_args(meta=True)
    def expr_pow(self, meta, value):
        return ExprPow(a=value[0], b=value[2], notes=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_deref(self, meta, value):
        return ExprDeref(addr=value[1], notes=value[0] + value[2], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_subscript(self, meta, value):
        return ExprSubscript(
            expr=value[0], offset=value[2], notes=value[1] + value[3], location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def atom_dot(self, meta, value):
        return ExprDot(expr=value[0], member=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_cast(self, meta, value):
        return ExprCast(
            expr=value[1],
            dest_type=value[3],
            notes=value[0] + value[2] + value[4],
            location=self.meta2loc(meta),
        )

    @v_args(meta=True)
    def atom_tuple_or_parentheses(self, meta, value):
        (arg_list,) = value
        assert isinstance(arg_list, ArgList)

        args = arg_list.args

        # Check if this is regular parentheses.
        if not arg_list.has_trailing_comma and len(args) == 1 and args[0].identifier is None:
            return ExprParentheses(
                val=args[0].expr, notes=arg_list.notes[0], location=arg_list.location
            )

        return ExprTuple(members=arg_list, location=self.meta2loc(meta))

    # Register.

    def reg_ap(self, value):
        return Register.AP

    def reg_fp(self, value):
        return Register.FP

    # Boolean expressions.

    @v_args(inline=True, meta=True)
    def bool_expr_eq(self, meta, a: Expression, notes: Notes, b: Expression):
        return BoolEqExpr(a=a, b=b, eq=True, notes=notes, location=self.meta2loc(meta))

    @v_args(inline=True, meta=True)
    def bool_expr_neq(self, meta, a: Expression, notes: Notes, b: Expression):
        return BoolEqExpr(a=a, b=b, eq=False, notes=notes, location=self.meta2loc(meta))

    @v_args(inline=True, meta=True)
    def bool_and_expr(self, meta, a: BoolExpr, notes: Notes, b: BoolEqExpr):
        return BoolAndExpr(a=a, b=b, notes=notes, location=self.meta2loc(meta))

    # Types.

    @v_args(meta=True)
    def modifier_local(self, meta, value):
        return Modifier(name="local", location=self.meta2loc(meta))

    @v_args(meta=True)
    def typed_identifier(self, meta, value):
        assert len(value) in [1, 2, 3], f"Unexpected argument: value={value}"
        modifier = None
        if isinstance(value[0], Modifier):
            modifier = value.pop(0)
        return TypedIdentifier(
            identifier=value[0],
            expr_type=value[1] if len(value) == 2 else None,
            modifier=modifier,
            location=self.meta2loc(meta),
        )

    # Instructions.

    @v_args(meta=True)
    def inst_assert_eq(self, meta, value):
        return AssertEqInstruction(a=value[0], b=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def code_element_compound_assert_eq(self, meta, value):
        return CodeElementCompoundAssertEq(a=value[0], b=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jmp_rel(self, meta, value):
        return JumpInstruction(val=value[0], relative=True, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jmp_abs(self, meta, value):
        return JumpInstruction(val=value[0], relative=False, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jmp_to_label(self, meta, value):
        return JumpToLabelInstruction(label=value[0], condition=None, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jnz(self, meta, value):
        if value[2] != "0":
            raise ParserError('Invalid syntax, expected "!= 0".', location=self.meta2loc(meta))
        return JnzInstruction(
            jump_offset=value[0], condition=value[1], location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def inst_jnz_to_label(self, meta, value):
        if value[2] != "0":
            raise ParserError('Invalid syntax, expected "!= 0".', location=self.meta2loc(meta))
        return JumpToLabelInstruction(
            label=value[0], condition=value[1], location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def inst_call_rel(self, meta, value):
        return CallInstruction(val=value[0], relative=True, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_call_abs(self, meta, value):
        return CallInstruction(val=value[0], relative=False, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_call_label(self, meta, value):
        return CallLabelInstruction(label=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_add_ap(self, meta, value):
        return AddApInstruction(expr=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_data_word(self, meta, value):
        return DefineWordInstruction(expr=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_ret(self, meta, value):
        return RetInstruction(location=self.meta2loc(meta))

    @v_args(meta=True)
    def instruction_noap(self, meta, value):
        return InstructionAst(body=value[0], inc_ap=False, location=self.meta2loc(meta))

    @v_args(meta=True)
    def instruction_ap(self, meta, value):
        return InstructionAst(body=value[0], inc_ap=True, location=self.meta2loc(meta))

    # RValues.

    @v_args(meta=True)
    def rvalue_expr(self, meta, value) -> Rvalue:
        (expr,) = value
        if isinstance(expr, ExprFuncCall):
            return expr.rvalue
        return RvalueExpr(expr=expr)

    def rvalue_call_instruction(self, value):
        (call_inst,) = value
        return RvalueCallInst(call_inst=call_inst)

    @v_args(meta=True)
    def function_call(self, meta, value):
        if len(value) == 2:
            func_ident, arg_list = value
            implicit_args = None
        elif len(value) == 3:
            func_ident, implicit_args, arg_list = value
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")

        return RvalueFuncCall(
            func_ident=func_ident,
            arguments=arg_list,
            implicit_arguments=implicit_args,
            location=self.meta2loc(meta),
        )

    # CairoFile.

    def code_element_instruction(self, value):
        return CodeElementInstruction(instruction=value[0])

    def code_element_const(self, value):
        return CodeElementConst(identifier=value[0], expr=value[1])

    def code_element_member(self, value):
        return CodeElementMember(typed_identifier=value[0])

    def code_element_reference(self, value):
        ref_binding, rvalue = value
        if isinstance(ref_binding, IdentifierList):
            return CodeElementUnpackBinding(unpacking_list=ref_binding, rvalue=rvalue)
        elif isinstance(ref_binding, TypedIdentifier):
            typed_identifier = ref_binding
            if isinstance(rvalue, RvalueCall):
                return CodeElementReturnValueReference(
                    typed_identifier=typed_identifier,
                    func_call=rvalue,
                )
            elif isinstance(rvalue, RvalueExpr):
                return CodeElementReference(typed_identifier=typed_identifier, expr=rvalue.expr)

        raise NotImplementedError(f"Unexpected argument: value={value}")

    @v_args(meta=True)
    def code_element_local_var(self, meta, value):
        if len(value) == 1:
            typed_identifier = value[0]
            expr = None
        elif len(value) == 2:
            typed_identifier, expr = value
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")

        return CodeElementLocalVariable(
            typed_identifier=typed_identifier, expr=expr, location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def code_element_temp_var(self, meta, value):
        typed_identifier, *maybe_expr = value
        (expr,) = maybe_expr if len(maybe_expr) > 0 else [None]

        return CodeElementTemporaryVariable(
            typed_identifier=typed_identifier,
            expr=expr,
            location=self.meta2loc(meta),
        )

    @v_args(meta=True)
    def code_element_static_assert(self, meta, value):
        return CodeElementStaticAssert(a=value[0], b=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def code_element_return(self, meta, value):
        (expr,) = value
        if isinstance(expr, ExprFuncCall):
            return CodeElementTailCall(func_call=expr.rvalue, location=self.meta2loc(meta))

        return CodeElementReturn(expr=expr, location=self.meta2loc(meta))

    def code_element_func_call(self, value):
        return CodeElementFuncCall(func_call=value[0])

    def code_element_label(self, value):
        identifier = value[0]
        if ScopedName.SEPARATOR in identifier.name:
            raise ParserError(
                f"Unexpected '{ScopedName.SEPARATOR}' in label name.", location=identifier.location
            )
        return CodeElementLabel(identifier=identifier)

    @v_args(meta=True)
    def code_element_hint(self, meta, value):
        return CodeElementHint(
            hint=ExprHint.from_str(val=value[0], location=self.meta2loc(meta)),
            location=self.meta2loc(meta),
        )

    def code_element_empty_line(self, value):
        return CodeElementEmptyLine()

    @v_args(meta=True)
    def commented_code_element(self, meta, value):
        comment = value[1][2:] if value[1] is not None else None
        return CommentedCodeElement(
            code_elm=value[0], comment=comment, location=self.meta2loc(meta)
        )

    def code_block(self, value):
        return CodeBlock(code_elements=value)

    @v_args(meta=True)
    def identifier_list(self, meta, value):
        identifiers = value[1:-1:3]
        # Join the notes before and after the comma.
        notes = [value[0]] + [value[i] + value[i + 1] for i in range(2, len(value) - 1, 3)]
        return IdentifierList(identifiers=identifiers, notes=notes, location=self.meta2loc(meta))

    def implicit_arguments(self, value):
        if len(value) == 0:
            return None
        elif len(value) == 1:
            return value[0]
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")

    def decorator(self, value):
        return value[0]

    def decorator_list(self, value):
        return value

    def code_element_function(self, value):
        decorators, identifier, implicit_arguments, arguments = value[:4]
        if len(value) == 6:
            # Return values present.
            returns = value[4]
            code_block = value[5]
        elif len(value) == 5:
            # Return values not present.
            returns = None
            code_block = value[4]
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")

        return CodeElementFunction(
            element_type="func",
            identifier=identifier,
            arguments=arguments,
            implicit_arguments=implicit_arguments,
            returns=returns,
            code_block=code_block,
            decorators=decorators,
        )

    def code_element_struct(self, value):
        decorators, identifier, code_block = value
        return CodeElementFunction(
            element_type="struct",
            identifier=identifier,
            arguments=IdentifierList(identifiers=[], notes=[]),
            implicit_arguments=None,
            returns=None,
            code_block=code_block,
            decorators=decorators,
        )

    def code_element_namespace(self, value):
        decorators, identifier, code_block = value
        return CodeElementFunction(
            element_type="namespace",
            identifier=identifier,
            arguments=IdentifierList(identifiers=[], notes=[]),
            implicit_arguments=None,
            returns=None,
            code_block=code_block,
            decorators=decorators,
        )

    @v_args(meta=True)
    def code_element_typedef(self, meta, value):
        return CodeElementTypeDef(
            identifier=value[0], cairo_type=value[1], location=self.meta2loc(meta)
        )

    def code_element_with(self, value):
        assert len(value) > 1
        return CodeElementWith(
            identifiers=value[:-1],
            code_block=value[-1],
        )

    def code_element_with_attr(self, value):
        assert len(value) >= 2
        attribute_value, notes = [], []
        for token in value[1:-1]:
            if type(token) is Notes:
                notes.append(token)
            else:
                attribute_value.append(token.value)

        return CodeElementWithAttr(
            attribute_name=value[0],
            attribute_value=attribute_value,
            code_block=value[-1],
            notes=notes,
        )

    @v_args(meta=True)
    def code_element_if(self, meta, value):
        condition = value[0]
        main_code_block = value[1]
        if len(value) == 2:
            else_code_block = None
        elif len(value) == 3:
            else_code_block = value[2]
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")

        # Create a location for the if keyword.
        location: Optional[Location] = None
        if not meta.empty:
            location = Location(
                start_line=meta.line,
                start_col=meta.column,
                end_line=meta.line,
                end_col=meta.column + len("if"),
                input_file=self.input_file,
            )

        return CodeElementIf(
            condition=condition,
            main_code_block=main_code_block,
            else_code_block=else_code_block,
            location=location,
        )

    @v_args(meta=True)
    def code_element_directive(self, meta, value):
        return CodeElementDirective(directive=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def directive_builtins(self, meta, value):
        builtins = [ident.name for ident in value[1:]]
        return BuiltinsDirective(builtins=builtins, location=self.meta2loc(meta))

    @v_args(meta=True)
    def directive_lang(self, meta, value):
        return LangDirective(name=value[1].name, location=self.meta2loc(meta))

    @v_args(meta=True)
    def aliased_identifier(self, meta, value):
        if len(value) == 1:
            # Element of the form: <identifier>.
            (identifier,) = value
            local_name = None
        elif len(value) == 2:
            # Element of the form: <identifier> as <local_name>.
            identifier, local_name = value
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")

        return AliasedIdentifier(
            orig_identifier=identifier, local_name=local_name, location=self.meta2loc(meta)
        )

    @v_args(meta=True)
    def code_element_import(self, meta, value):
        path = value[0]
        if isinstance(value[1], AliasedIdentifier):
            # Single line.
            import_items = value[1:]
            notes = []
        else:
            # Multiline.
            assert len(value) % 3 == 2, f"Unexpected value {value}."
            import_items = value[2::3]
            # Join the notes before and after the comma.
            notes = [value[1]] + [value[i] + value[i + 1] for i in range(3, len(value) - 1, 3)]

        return CodeElementImport(
            path=path,
            import_items=import_items,
            notes=notes,
            location=self.meta2loc(meta),
        )

    @v_args(meta=True)
    def code_element_alloc_locals(self, meta, value):
        return CodeElementAllocLocals(location=self.meta2loc(meta))

    def cairo_file(self, value):
        return CairoFile(code_block=value[0])

    # Notes.

    def note_new_line(self, value):
        return "\n"

    @v_args(meta=True)
    def notes(self, meta, value):
        """
        Collects the comments in the AST node, marking whether the notes starts with a new line.
        """
        # Does the note start with a new line.
        starts_new_line = False
        # Whether we saw comments. This is used to determine whether a new line is on the beginning
        # of the notes.
        saw_comment = False
        comments = []

        for v in value:
            if v == "\n":
                if not saw_comment:
                    starts_new_line = True
            else:
                comments.append(v.value)
                saw_comment = True
        return Notes(
            comments=comments, starts_new_line=starts_new_line, location=self.meta2loc(meta)
        )

    def meta2loc(self, meta: lark.tree.Meta) -> Optional[Location]:
        if meta.empty:
            return None
        return Location(
            start_line=meta.line,
            start_col=meta.column,
            end_line=meta.end_line,
            end_col=meta.end_column,
            input_file=self.input_file,
            parent_location=self.parser_context.parent_location,
        )

    def token2loc(self, token: Token) -> Location:
        return Location(
            start_line=as_non_optional(token.line),
            start_col=as_non_optional(token.column),
            end_line=as_non_optional(token.end_line),
            end_col=as_non_optional(token.end_column),
            input_file=self.input_file,
            parent_location=self.parser_context.parent_location,
        )


def backslash_to_hex(value: bytes) -> bytes:
    r"""
    Replaces substrings of the form '\x**' with the corresponding byte.
    """
    pattern = rb"\\x([0-9a-fA-F]{2})"
    replacer = lambda m: bytes.fromhex(m.group(1).decode("ascii"))
    return re.sub(pattern, replacer, value)
