python_lib(cairo_version_lib
    PREFIX starkware/cairo/lang

    FILES
    VERSION
    version.py
)

if (NOT DEFINED CAIRO_PYTHON_INTERPRETER)
    set(CAIRO_PYTHON_INTERPRETER python3.9)
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
    PYTHON ${PYTHON_COMMAND}
    LIBS
    cairo_bootloader_generate_fact_lib
    cairo_common_lib
    cairo_compile_lib
    cairo_compile_test_utils_lib
    cairo_hash_program_lib
    cairo_run_lib
    cairo_script_lib
    program_hash_test_utils_lib
    sharp_client_config_lib
    sharp_client_lib
    starknet_block_hash_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_state_lib
    starknet_script_lib
    starknet_sequencer_api_utils_lib
    starknet_testing_lib
    starkware_eth_test_utils_lib
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
