python_lib(cairo_migrator_lib
    PREFIX starkware/cairo/lang/migrators

    FILES
    migrator_grammar.ebnf
    migrator.py

    LIBS
    cairo_compile_lib
)

full_python_test(cairo_migrator_test
    PREFIX starkware/cairo/lang/migrators
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/migrators

    FILES
    migrator_test.py

    LIBS
    cairo_migrator_lib
    cairo_compile_lib
    pip_pytest
)

python_venv(cairo_migrator_venv
    PYTHON ${PYTHON_COMMAND}
    LIBS
    cairo_migrator_lib
)

python_exe(cairo_migrator
    VENV cairo_migrator_venv
    MODULE starkware.cairo.lang.migrators.migrator
)
