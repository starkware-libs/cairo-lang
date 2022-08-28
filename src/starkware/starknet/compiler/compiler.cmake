if (NOT DEFINED CAIRO_PYTHON_INTERPRETER)
    set(CAIRO_PYTHON_INTERPRETER python3.9)
endif()
if (NOT DEFINED STARKNET_COMPILE_LIB)
    set(STARKNET_COMPILE_LIB pip_cairo_lang)
endif()

python_venv(starknet_compile_venv
    PYTHON ${CAIRO_PYTHON_INTERPRETER}

    LIBS
    ${STARKNET_COMPILE_LIB}
)

python_exe(starknet_compile_exe
    VENV starknet_compile_venv
    MODULE starkware.starknet.compiler.compile
)
