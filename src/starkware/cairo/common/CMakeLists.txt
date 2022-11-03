add_subdirectory(cairo_blake2s)

python_lib(cairo_common_lib
    PREFIX starkware/cairo/common
    FILES
    alloc.cairo
    bitwise.cairo
    bool.cairo
    cairo_blake2s/blake2s.cairo
    cairo_blake2s/blake2s_utils.py
    cairo_blake2s/packed_blake2s.cairo
    cairo_builtins.cairo
    cairo_keccak/keccak.cairo
    cairo_keccak/keccak_utils.py
    cairo_keccak/packed_keccak.cairo
    cairo_secp/bigint.cairo
    cairo_secp/constants.cairo
    cairo_secp/ec.cairo
    cairo_secp/field.cairo
    cairo_secp/secp_utils.py
    cairo_secp/signature.cairo
    cairo_sha256/sha256_utils.py
    default_dict.cairo
    dict_access.cairo
    dict.cairo
    dict.py
    ec.cairo
    ec_point.cairo
    find_element.cairo
    hash_chain.cairo
    hash_chain.py
    hash_state.cairo
    hash_state.py
    hash.cairo
    invoke.cairo
    keccak.cairo
    keccak_state.cairo
    math_cmp.cairo
    math_utils.py
    math.cairo
    memcpy.cairo
    memset.cairo
    merkle_multi_update.cairo
    merkle_update.cairo
    patricia_utils.py
    patricia.cairo
    pow.cairo
    registers.cairo
    segments.cairo
    serialize.cairo
    set.cairo
    signature.cairo
    small_merkle_tree.cairo
    small_merkle_tree.py
    squash_dict.cairo
    structs.py
    uint256.cairo
    usort.cairo
    ${CAIRO_COMMON_LIB_ADDITIONAL_FILES}

    LIBS
    cairo_vm_crypto_lib
    starkware_python_utils_lib
    starkware_merkle_tree_lib
    ${CAIRO_COMMON_LIB_ADDITIONAL_LIBS}
)

python_lib(cairo_common_validate_utils_lib
    PREFIX starkware/cairo/common
    FILES
    validate_utils.py

    LIBS
    cairo_run_builtins_lib
    cairo_run_lib
    cairo_vm_lib
    starkware_python_utils_lib
)

python_lib(cairo_function_runner_lib
    PREFIX starkware/cairo/common

    FILES
    cairo_function_runner.py

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_run_builtins_lib
    cairo_run_lib
    cairo_tracer_lib
    cairo_vm_crypto_lib
    cairo_vm_lib
)
