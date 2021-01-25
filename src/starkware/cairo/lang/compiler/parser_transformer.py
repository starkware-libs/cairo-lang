import re
from typing import Optional

from lark import Transformer, v_args

from starkware.cairo.lang.compiler.ast.arguments import IdentifierList
from starkware.cairo.lang.compiler.ast.bool_expr import BoolExpr
from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective, CodeBlock, CodeElementAllocLocals, CodeElementCompoundAssertEq,
    CodeElementConst, CodeElementDirective, CodeElementEmptyLine, CodeElementFuncCall,
    CodeElementFunction, CodeElementHint, CodeElementIf, CodeElementImport, CodeElementInstruction,
    CodeElementLabel, CodeElementLocalVariable, CodeElementMember, CodeElementReference,
    CodeElementReturn, CodeElementReturnValueReference, CodeElementStaticAssert,
    CodeElementTemporaryVariable, CodeElementUnpackBinding, CommentedCodeElement)
from starkware.cairo.lang.compiler.ast.expr import (
    ArgList, EllipsisSymbol, ExprAddressOf, ExprAssignment, ExprCast, ExprConst, ExprDeref,
    ExprIdentifier, ExprNeg, ExprOperator, ExprParentheses, ExprPyConst, ExprReg, ExprTuple)
from starkware.cairo.lang.compiler.ast.imports import ImportItem
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction, AssertEqInstruction, CallInstruction, CallLabelInstruction, InstructionAst,
    JnzInstruction, JumpInstruction, JumpToLabelInstruction, RetInstruction)
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.ast.notes import Notes
from starkware.cairo.lang.compiler.ast.rvalue import (
    RvalueCall, RvalueCallInst, RvalueExpr, RvalueFuncCall)
from starkware.cairo.lang.compiler.ast.types import Modifier, TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import InputFile, Location, LocationError
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class ParserError(LocationError):
    pass


class ParserTransformer(Transformer):
    """
    Transforms the lark tree into an AST based on the classes defined in ast/*.py.
    """

    def __init__(self, input_file: InputFile):
        self.input_file = input_file

    def __default__(self, data: str, children, meta):
        raise TypeError(f'Unable to parse tree node of type {data}')

    # Types.

    @v_args(meta=True)
    def type_felt(self, value, meta):
        return TypeFelt(location=self.meta2loc(meta))

    def type_struct(self, value):
        assert len(value) == 1 and isinstance(value[0], ExprIdentifier)
        return TypeStruct(
            scope=ScopedName.from_string(value[0].name),
            is_fully_resolved=False,
            location=value[0].location)

    @v_args(meta=True)
    def type_pointer(self, value, meta):
        return TypePointer(pointee=value[0], location=self.meta2loc(meta))

    # Expression.
    @v_args(meta=True)
    def arg_list(self, value, meta):
        if len(value) % 3 == 1:
            has_trailing_comma = True
        else:
            has_trailing_comma = False
            assert len(value) % 3 == 0
            value.append(Notes())
        args = value[1::3]
        # Join the notes before and after the comma.
        notes = [
            prev_after + before
            for before, prev_after
            in zip(value[::3], [Notes()] + value[2::3])]
        return ArgList(
            args=args, notes=notes, has_trailing_comma=has_trailing_comma,
            location=self.meta2loc(meta))

    @v_args(meta=True)
    def ellipsis(self, value, meta):
        return EllipsisSymbol(location=self.meta2loc(meta))

    @v_args(meta=True)
    def expr_assignment(self, value, meta):
        if len(value) == 1:
            identifier = None
            expr = value[0]
        elif len(value) == 2:
            identifier, expr = value
        else:
            raise NotImplementedError(f'Unexpected argument: value={value}')
        return ExprAssignment(identifier=identifier, expr=expr, location=self.meta2loc(meta))

    @v_args(meta=True)
    def identifier(self, value, meta):
        return ExprIdentifier(name='.'.join(x.value for x in value), location=self.meta2loc(meta))

    @v_args(meta=True)
    def identifier_def(self, value, meta):
        return ExprIdentifier(name=value[0].value, location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_number(self, value, meta):
        return ExprConst(val=int(value[0]), location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_pyconst(self, value, meta):
        return ExprPyConst.from_str(src=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_reg(self, value, meta):
        return ExprReg(reg=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def expr_add(self, value, meta):
        return ExprOperator(
            a=value[0], op='+', b=value[2], notes=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def expr_sub(self, value, meta):
        return ExprOperator(
            a=value[0], op='-', b=value[2], notes=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def expr_mul(self, value, meta):
        return ExprOperator(
            a=value[0], op='*', b=value[2], notes=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def expr_div(self, value, meta):
        return ExprOperator(
            a=value[0], op='/', b=value[2], notes=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def unary_addressof(self, value, meta):
        return ExprAddressOf(expr=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def unary_neg(self, value, meta):
        return ExprNeg(val=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_parentheses(self, value, meta):
        return ExprParentheses(val=value[1], notes=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_deref(self, value, meta):
        return ExprDeref(addr=value[1], notes=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_cast(self, value, meta):
        return ExprCast(
            expr=value[1], notes=value[0], dest_type=value[2], location=self.meta2loc(meta))

    @v_args(meta=True)
    def atom_tuple(self, value, meta):
        return ExprTuple(members=value[0], location=self.meta2loc(meta))

    # Register.

    def reg_ap(self, value):
        return Register.AP

    def reg_fp(self, value):
        return Register.FP

    # Boolean expresions.

    @v_args(meta=True)
    def bool_expr_eq(self, value, meta):
        return BoolExpr(a=value[0], b=value[1], eq=True, location=self.meta2loc(meta))

    @v_args(meta=True)
    def bool_expr_neq(self, value, meta):
        return BoolExpr(a=value[0], b=value[1], eq=False, location=self.meta2loc(meta))

    # Types.

    @v_args(meta=True)
    def modifier_local(self, value, meta):
        return Modifier(name='local', location=self.meta2loc(meta))

    @v_args(meta=True)
    def typed_identifier(self, value, meta):
        assert len(value) in [1, 2, 3], f'Unexpected argument: value={value}'
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
    def inst_assert_eq(self, value, meta):
        return AssertEqInstruction(a=value[0], b=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def code_element_compound_assert_eq(self, value, meta):
        return CodeElementCompoundAssertEq(a=value[0], b=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jmp_rel(self, value, meta):
        return JumpInstruction(val=value[0], relative=True, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jmp_abs(self, value, meta):
        return JumpInstruction(val=value[0], relative=False, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jmp_to_label(self, value, meta):
        return JumpToLabelInstruction(label=value[0], condition=None, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jnz(self, value, meta):
        if value[2] != '0':
            raise ParserError('Invalid syntax, expected "!= 0".', location=self.meta2loc(meta))
        return JnzInstruction(
            jump_offset=value[0], condition=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_jnz_to_label(self, value, meta):
        if value[2] != '0':
            raise ParserError('Invalid syntax, expected "!= 0".', location=self.meta2loc(meta))
        return JumpToLabelInstruction(
            label=value[0], condition=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_call_rel(self, value, meta):
        return CallInstruction(val=value[0], relative=True, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_call_abs(self, value, meta):
        return CallInstruction(val=value[0], relative=False, location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_call_label(self, value, meta):
        return CallLabelInstruction(label=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_add_ap(self, value, meta):
        return AddApInstruction(expr=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def inst_ret(self, value, meta):
        return RetInstruction(location=self.meta2loc(meta))

    @v_args(meta=True)
    def instruction_noap(self, value, meta):
        return InstructionAst(body=value[0], inc_ap=False, location=self.meta2loc(meta))

    @v_args(meta=True)
    def instruction_ap(self, value, meta):
        return InstructionAst(body=value[0], inc_ap=True, location=self.meta2loc(meta))

    # RValues.

    def rvalue_expr(self, value):
        expr, = value
        return RvalueExpr(expr=expr)

    def rvalue_call_instruction(self, value):
        call_inst, = value
        return RvalueCallInst(call_inst=call_inst)

    @v_args(meta=True)
    def function_call(self, value, meta):
        func_ident, arg_list = value
        return RvalueFuncCall(
            func_ident=func_ident, exprs=arg_list.args, notes=arg_list.notes,
            location=self.meta2loc(meta))

    # CairoFile.

    def code_element_instruction(self, value):
        return CodeElementInstruction(instruction=value[0])

    def code_element_const(self, value):
        return CodeElementConst(identifier=value[0], expr=value[1])

    def code_element_member(self, value):
        return CodeElementMember(typed_identifier=value[0], expr=value[1])

    def code_element_reference(self, value):
        ref_binding, rvalue = value
        if isinstance(ref_binding, IdentifierList):
            return CodeElementUnpackBinding(
                unpacking_list=ref_binding, rvalue=rvalue)
        elif isinstance(ref_binding, TypedIdentifier):
            typed_identifier = ref_binding
            if isinstance(rvalue, RvalueCall):
                return CodeElementReturnValueReference(
                    typed_identifier=typed_identifier,
                    func_call=rvalue,
                )
            elif isinstance(rvalue, RvalueExpr):
                return CodeElementReference(typed_identifier=typed_identifier, expr=rvalue.expr)

        raise NotImplementedError(f'Unexpected argument: value={value}')

    @v_args(meta=True)
    def code_element_local_var(self, value, meta):
        if len(value) == 1:
            typed_identifier = value[0]
            expr = None
        elif len(value) == 2:
            typed_identifier, expr = value
        else:
            raise NotImplementedError(f'Unexpected argument: value={value}')

        return CodeElementLocalVariable(
            typed_identifier=typed_identifier, expr=expr, location=self.meta2loc(meta))

    @v_args(meta=True)
    def code_element_temp_var(self, value, meta):
        return CodeElementTemporaryVariable(
            typed_identifier=value[0], expr=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def code_element_static_assert(self, value, meta):
        return CodeElementStaticAssert(a=value[0], b=value[1], location=self.meta2loc(meta))

    @v_args(meta=True)
    def code_element_return(self, value, meta):
        arglist, = value
        return CodeElementReturn(exprs=arglist.args, location=self.meta2loc(meta))

    def code_element_func_call(self, value):
        return CodeElementFuncCall(func_call=value[0])

    def code_element_label(self, value):
        return CodeElementLabel(identifier=value[0])

    @v_args(meta=True)
    def code_element_hint(self, value, meta):
        HINT_PATTERN = r'%\{(?P<prefix_whitespace>([ \t]*\n)*)(?P<code>.*?)%\}'
        m = re.match(HINT_PATTERN, value[0], re.DOTALL)
        assert m is not None
        code = m.group('code').rstrip()
        if code is None:
            code = ''

        # Remove common indentation.
        lines = code.split('\n')
        common_indent = min(
            (len(line) - len(line.lstrip(' ')) for line in lines if line),
            default=0)
        code = '\n'.join(line[common_indent:] for line in lines)
        return CodeElementHint(
            hint_code=code,
            n_prefix_newlines=m.group('prefix_whitespace').count('\n'),
            location=self.meta2loc(meta))

    def code_element_empty_line(self, value):
        return CodeElementEmptyLine()

    def commented_code_element(self, value):
        comment = value[1][1:] if len(value) == 2 else None
        return CommentedCodeElement(code_elm=value[0], comment=comment)

    def code_block(self, value):
        return CodeBlock(code_elements=value)

    @v_args(meta=True)
    def identifier_list(self, value, meta):
        identifiers = value[1:-1:3]
        # Join the notes before and after the comma.
        notes = [value[0]] + [value[i] + value[i + 1] for i in range(2, len(value) - 1, 3)]
        return IdentifierList(identifiers=identifiers, notes=notes, location=self.meta2loc(meta))

    def code_element_function(self, value):
        identifier = value[0]
        arguments = value[1]

        if len(value) == 4:
            # Return values present.
            returns = value[2]
            code_block = value[3]
        elif len(value) == 3:
            # Return values not present.
            returns = None
            code_block = value[2]
        else:
            raise NotImplementedError(f'Unexpected argument: value={value}')

        return CodeElementFunction(
            element_type='func', identifier=identifier, arguments=arguments,
            returns=returns, code_block=code_block)

    def code_element_struct(self, value):
        element_type, identifier, code_block = value
        return CodeElementFunction(
            element_type=element_type.value,
            identifier=identifier,
            arguments=IdentifierList(identifiers=[], notes=[]),
            returns=None,
            code_block=code_block,
        )

    @v_args(meta=True)
    def code_element_if(self, value, meta):
        condition = value[0]
        main_code_block = value[1]
        if len(value) == 2:
            else_code_block = None
        elif len(value) == 3:
            else_code_block = value[2]
        else:
            raise NotImplementedError(f'Unexpected argument: value={value}')

        # Create a location for the if keyword.
        location: Optional[Location] = None
        if not meta.empty:
            location = Location(
                start_line=meta.line,
                start_col=meta.column,
                end_line=meta.line,
                end_col=meta.column + len('if'),
                input_file=self.input_file,
            )

        return CodeElementIf(
            condition=condition, main_code_block=main_code_block, else_code_block=else_code_block,
            location=location)

    @v_args(meta=True)
    def code_element_directive(self, value, meta):
        return CodeElementDirective(directive=value[0], location=self.meta2loc(meta))

    @v_args(meta=True)
    def directive_builtins(self, value, meta):
        builtins = [ident.name for ident in value]
        return BuiltinsDirective(builtins=builtins, location=self.meta2loc(meta))

    @v_args(meta=True)
    def import_item(self, value, meta):
        if len(value) == 1:
            # Element of the form: <identifier>.
            identifier, = value
            local_name = None
        elif len(value) == 2:
            # Element of the form: <identifier> as <local_name>.
            identifier, local_name = value
        else:
            raise NotImplementedError(f'Unexpected argument: value={value}')

        return ImportItem(
            orig_identifier=identifier,
            local_name=local_name,
            location=self.meta2loc(meta))

    @v_args(meta=True)
    def code_element_import(self, value, meta):
        path = value[0]
        if isinstance(value[1], ImportItem):
            # Single line.
            import_items = value[1:]
            notes = []
        else:
            # Multiline.
            assert len(value) % 3 == 2, f'Unexpected value {value}.'
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
    def code_element_alloc_locals(self, value, meta):
        return CodeElementAllocLocals(location=self.meta2loc(meta))

    def cairo_file(self, value):
        return CairoFile(code_block=value[0])

    # Notes.

    def note_new_line(self, value):
        return '\n'

    @v_args(meta=True)
    def notes(self, value, meta):
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
            if v == '\n':
                if not saw_comment:
                    starts_new_line = True
            else:
                comments.append(v.value)
                saw_comment = True
        return Notes(
            comments=comments, starts_new_line=starts_new_line, location=self.meta2loc(meta))

    def meta2loc(self, meta):
        if meta.empty:
            return None
        return Location(
            start_line=meta.line,
            start_col=meta.column,
            end_line=meta.end_line,
            end_col=meta.end_column,
            input_file=self.input_file,
        )
