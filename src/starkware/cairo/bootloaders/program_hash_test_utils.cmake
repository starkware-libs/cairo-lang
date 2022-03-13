python_lib(program_hash_test_utils_lib
    PREFIX starkware/cairo/bootloaders

    FILES
    program_hash_test_utils.py

    LIBS
    ${PROGRAM_HASH_TEST_UTILS_LIB_ADDITIONAL_LIBS}
)
