python_lib(cairo_version_lib
    PREFIX starkware/cairo/lang

    FILES
    VERSION
    version.py
)

if (NOT DEFINED CAIRO_PYTHON_INTERPRETER)
    set(CAIRO_PYTHON_INTERPRETER python3.7)
endif()

python_venv(cairo_lang_venv
    PYTHON ${CAIRO_PYTHON_INTERPRETER}
    LIBS
    cairo_bootloader_generate_fact_lib
    cairo_common_lib
    cairo_compile_lib
    cairo_hash_program_lib
    cairo_run_lib
    cairo_script_lib
    ${CAIRO_LANG_VENV_ADDITIONAL_LIBS}
)

python_venv(cairo_lang_package_venv
    PYTHON python3.7
    LIBS
    cairo_bootloader_generate_fact_lib
    cairo_common_lib
    cairo_compile_lib
    cairo_hash_program_lib
    cairo_run_lib
    cairo_script_lib
    sharp_client_config_lib
    sharp_client_lib
    starknet_script_lib
)

python_lib(cairo_instances_lib
    PREFIX starkware/cairo/lang

    FILES
    instances.py
    ${CAIRO_INSTANCES_LIB_ADDITIONAL_FILES}

    LIBS
    cairo_run_builtins_lib
)

python_lib(cairo_constants_lib
    PREFIX starkware/cairo/lang

    FILES
    cairo_constants.py
)
