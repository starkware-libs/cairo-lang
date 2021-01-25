python_lib(cairo_hash_program_lib
    PREFIX starkware/cairo/bootloader

    FILES
    hash_program.py

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_version_lib
    cairo_vm_crypto_lib
)

python_venv(cairo_hash_program_venv
    PYTHON python3.7
    LIBS
    cairo_hash_program_lib
)

python_exe(cairo_hash_program_exe
    VENV cairo_hash_program_venv
    MODULE starkware.cairo.bootloader.hash_program
)

full_python_test(cairo_hash_program_test
    PREFIX starkware/cairo/bootloader
    PYTHON python3.7
    TESTED_MODULES starkware/cairo/bootloader

    FILES
    hash_program_test.py

    LIBS
    cairo_hash_program_lib
    pip_pytest
)
