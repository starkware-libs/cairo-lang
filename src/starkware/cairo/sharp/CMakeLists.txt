python_lib(fact_checker_lib
    PREFIX starkware/cairo/sharp

    FILES
    fact_checker.py

    LIBS
    pip_web3
)

full_python_test(fact_checker_test
    PREFIX starkware/cairo/sharp
    PYTHON ${PYTHON_COMMAND}

    FILES
    fact_checker_test.py

    LIBS
    fact_checker_lib
    pip_pytest
)

python_lib(sharp_client_lib
    PREFIX starkware/cairo/sharp

    FILES
    client_lib.py
    sharp_client.py

    LIBS
    cairo_bootloader_generate_fact_lib
    cairo_hash_program_lib
    cairo_vm_crypto_lib
    cairo_vm_lib
    fact_checker_lib
    pip_urllib3
)

full_python_test(sharp_client_lib_test
    PREFIX starkware/cairo/sharp
    PYTHON ${PYTHON_COMMAND}

    FILES
    client_lib_test.py
    sharp_client_test.py

    LIBS
    cairo_script_lib
    sharp_client_lib
    pip_pytest
)

python_lib(sharp_client_config_lib
    PREFIX starkware/cairo/sharp

    FILES
    config.json
)
