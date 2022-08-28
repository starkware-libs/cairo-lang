full_python_test(cairo_blake2s_test
    PREFIX starkware/cairo/common/cairo_blake2s
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/common

    FILES
    blake2s_test.cairo
    blake2s_test.py

    LIBS
    cairo_common_lib
    cairo_constants_lib
    cairo_function_runner_lib
    pip_pytest
    pip_pytest_asyncio
)
