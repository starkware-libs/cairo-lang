from typing import List, Optional, Sequence, Tuple

from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManager, PassManagerContext
from starkware.cairo.lang.compiler.preprocessor.preprocessor import PreprocessedProgram
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def preprocess_codes(
    codes: Sequence[Tuple[str, str]],
    pass_manager: PassManager,
    main_scope: ScopedName = ScopedName(),
    start_codes: Optional[List[Tuple[str, str]]] = None,
) -> PreprocessedProgram:
    """
    Preprocesses a list of Cairo files and returns a PreprocessedProgram instance.
    codes is a list of pairs (code_string, file_name).
    """
    context = PassManagerContext(
        codes=list(codes),
        main_scope=main_scope,
        identifiers=IdentifierManager(),
        start_codes=[] if start_codes is None else start_codes,
    )

    pass_manager.run(context)

    assert context.preprocessed_program is not None
    return context.preprocessed_program
