python_lib(starknet_security_lib
    PREFIX starkware/starknet/security
    FILES
    secure_hints.py

    LIBS
    cairo_compile_lib
    cairo_run_lib
    pip_marshmallow
    pip_marshmallow_dataclass
)

full_python_test(starknet_hints_latest_whitelist_test
    PREFIX starkware/starknet/security
    PYTHON python3.7
    TESTED_MODULES starkware/starknet/security

    FILES
    latest_whitelist_test.py
    secure_hints_test.py
    starknet_common.cairo

    LIBS
    cairo_common_lib
    cairo_constants_lib
    starknet_common_lib
    starknet_security_lib
    pip_pytest
)

python_exe(starknet_hints_latest_whitelist_fix
    VENV starknet_hints_latest_whitelist_test_venv
    MODULE starkware.starknet.security.latest_whitelist_test
    ARGS "--fix"
)

python_lib(starknet_hints_whitelist_lib
    PREFIX starkware/starknet/security

    FILES
    hints_whitelist.py
    whitelists/latest.json

    LIBS
    starknet_security_lib
)
