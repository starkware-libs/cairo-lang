import starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils as utils
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.bool_expr.errors import BoolExprLoweringError
from starkware.cairo.lang.compiler.preprocessor.bool_expr.lowering import BoolExprLoweringStage
from starkware.cairo.lang.compiler.preprocessor.default_pass_manager import ModuleCollector
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManager, PassManagerContext
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict


def lower_and_format(code: str) -> str:
    manager = PassManager()
    manager.add_stage(
        "module_collector",
        ModuleCollector(
            read_module=read_file_from_dict(utils.CAIRO_TEST_MODULES),
            additional_modules=[
                "starkware.cairo.lang.compiler.lib.registers",
            ],
        ),
    )
    manager.add_stage("bool_expr_lowering", BoolExprLoweringStage())

    context = PassManagerContext(
        codes=[(code, "")],
        main_scope=utils.TEST_SCOPE,
        identifiers=IdentifierManager(),
        start_codes=[],
    )

    manager.run(context)

    module = context.modules[-1]

    return module.format(allowed_line_length=100)


def verify_exception(*args, **kwargs):
    kwargs = kwargs.copy()
    kwargs["exc_type"] = BoolExprLoweringError
    utils.verify_exception(*args, **kwargs)
