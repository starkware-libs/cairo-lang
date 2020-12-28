python_lib(cairo_common_lib
    PREFIX starkware/cairo/common
    FILES
    alloc.cairo
    cairo_builtins.cairo
    dict.cairo
    dict.py
    find_element.cairo
    hash.cairo
    hash_chain.cairo
    hash_chain.py
    hash_state.cairo
    math.cairo
    math_utils.py
    memcpy.cairo
    merkle_multi_update.cairo
    merkle_update.cairo
    registers.cairo
    serialize.cairo
    signature.cairo
    ${CAIRO_COMMON_LIB_ADDITIONAL_FILES}

    LIBS
    ${CAIRO_COMMON_LIB_ADDITIONAL_LIBS}
)
