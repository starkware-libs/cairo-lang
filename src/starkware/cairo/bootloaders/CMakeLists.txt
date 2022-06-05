set(PROGRAM_HASH_TEST_UTILS_LIB_ADDITIONAL_LIBS cairo_hash_program_lib)

add_subdirectory(bootloader)
add_subdirectory(simple_bootloader)

include(program_hash_test_utils.cmake)

python_lib(cairo_hash_program_lib
    PREFIX starkware/cairo/bootloaders

    FILES
    hash_program.py

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_version_lib
    cairo_vm_crypto_lib
    starkware_python_utils_lib
)

python_venv(cairo_hash_program_venv
    PYTHON ${PYTHON_COMMAND}
    LIBS
    cairo_hash_program_lib
)

python_exe(cairo_hash_program_exe
    VENV cairo_hash_program_venv
    MODULE starkware.cairo.bootloaders.hash_program
)

python_lib(cairo_bootloader_fact_topology_lib
    PREFIX starkware/cairo/bootloaders
    FILES
    fact_topology.py

    LIBS
    pip_marshmallow
    pip_marshmallow_dataclass
)

python_lib(cairo_bootloader_generate_fact_lib
    PREFIX starkware/cairo/bootloaders
    FILES
    compute_fact.py
    generate_fact.py

    LIBS
    cairo_bootloader_fact_topology_lib
    cairo_hash_program_lib
    cairo_relocatable_lib
    cairo_vm_lib
    starkware_python_utils_lib
    pip_eth_hash
    pip_pycryptodome
)
