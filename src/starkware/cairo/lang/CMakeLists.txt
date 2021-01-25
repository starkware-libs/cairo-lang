add_subdirectory(builtins)
add_subdirectory(compiler)
add_subdirectory(scripts)
add_subdirectory(tracer)
add_subdirectory(vm)

python_lib(cairo_version_lib
    PREFIX starkware/cairo/lang

    FILES
    VERSION
    version.py
)

python_venv(cairo_lang_venv
    PYTHON python3.7
    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_hash_program_lib
    cairo_run_lib
    cairo_script_lib
    ${CAIRO_LANG_VENV_ADDITIONAL_LIBS}
)

python_lib(cairo_instances_lib
    PREFIX starkware/cairo/lang

    FILES
    instances.py

    LIBS
    cairo_run_builtins_lib
)
