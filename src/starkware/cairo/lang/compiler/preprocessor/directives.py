from typing import List, Optional

from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective,
    CodeElementDirective,
    Directive,
)
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManagerContext, Stage
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError


class DirectivesCollectorStage(Stage):
    def __init__(self):
        self.builtins: Optional[List[str]] = None

    def run(self, context: PassManagerContext):
        for module in context.modules:
            for commented_code_elm in module.cairo_file.code_block.code_elements:
                code_elm = commented_code_elm.code_elm
                if isinstance(code_elm, CodeElementDirective):
                    self.handle_directive(code_elm.directive)

        # Finalize.
        context.builtins = self.builtins

    def handle_directive(self, directive: Directive):
        if isinstance(directive, BuiltinsDirective):
            self.handle_builtin_directive(directive)

    def handle_builtin_directive(self, directive: BuiltinsDirective):
        if self.builtins is not None:
            raise PreprocessorError(
                "Redefinition of builtins directive.",
                location=directive.location,
            )

        seen_builtins = set()
        for builtin in directive.builtins:
            if builtin in seen_builtins:
                raise PreprocessorError(
                    f"The builtin '{builtin}' appears twice in builtins directive.",
                    location=directive.location,
                )

            seen_builtins.add(builtin)

        self.builtins = directive.builtins
