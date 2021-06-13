from typing import Sequence, Tuple

from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManager, PassManagerContext
from starkware.cairo.lang.compiler.preprocessor.preprocessor import PreprocessedProgram
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def preprocess_codes(
        codes: Sequence[Tuple[str, str]], pass_manager: PassManager,
        main_scope: ScopedName = ScopedName()) -> PreprocessedProgram:
    """
    Preprocesses a list of Cairo files and returns a PreprocessedProgram instance.
    codes is a list of pairs (code_string, file_name).
    """
    context = PassManagerContext(
        codes=list(codes),
        main_scope=main_scope,
        identifiers=IdentifierManager(),
    )

    pass_manager.run(context)

    assert context.preprocessed_program is not None
    return context.preprocessed_program
