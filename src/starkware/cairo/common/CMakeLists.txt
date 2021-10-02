python_lib(cairo_common_lib
    PREFIX starkware/cairo/common
    FILES
    alloc.cairo
    bitwise.cairo
    cairo_builtins.cairo
    cairo_blake2s/blake2s_utils.py
    cairo_keccak/keccak_utils.py
    cairo_sha256/sha256_utils.py
    default_dict.cairo
    dict_access.cairo
    dict.cairo
    dict.py
    ec_point.cairo
    find_element.cairo
    hash_chain.cairo
    hash_chain.py
    hash_state.cairo
    hash.cairo
    invoke.cairo
    keccak.cairo
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
    ${CAIRO_COMMON_LIB_ADDITIONAL_FILES}

    LIBS
    cairo_vm_crypto_lib
    starkware_python_utils_lib
    starkware_merkle_tree_lib
    ${CAIRO_COMMON_LIB_ADDITIONAL_LIBS}
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
