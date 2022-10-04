python_lib(starknet_security_lib
    PREFIX starkware/starknet/security
    FILES
    secure_hints.py
    simple_references.py

    LIBS
    cairo_compile_lib
    starkware_dataclasses_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
)

full_python_test(starknet_hints_latest_whitelist_test
    PREFIX starkware/starknet/security
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/security

    FILES
    latest_whitelist_test.py
    secure_hints_test.py
    simple_references_test.py
    starknet_common.cairo

    LIBS
    cairo_common_lib
    cairo_constants_lib
    starknet_common_lib
    starknet_hints_whitelist_lib
    starknet_security_lib
    starkware_python_utils_lib
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
    whitelists/0.6.0.json
    whitelists/0.8.2.json
    whitelists/384_bit_prime_field.json
    whitelists/cairo_blake2s.json
    whitelists/cairo_keccak.json
    whitelists/cairo_secp.json
    whitelists/cairo_sha256.json
    whitelists/cairo_sha256_arbitrary_input_length.json
    whitelists/ec_bigint.json
    whitelists/ec_recover.json
    whitelists/latest.json

    LIBS
    starknet_security_lib
)
