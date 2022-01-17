# Compiles a StarkNet Contract.
# Usage example:
#   starknet_compile(mytarget contract_compiled.json contract.cairo "--debug_info_with_source")
function(starknet_compile TARGET_NAME COMPILED_PROGRAM_NAME SOURCE_FILE COMPILE_FLAGS)
    cairo_compile_base(
        ${TARGET_NAME}
        "${CMAKE_BINARY_DIR}/src/starkware/starknet/compiler/starknet_compile_exe"
        "${COMPILED_PROGRAM_NAME}"
        "${SOURCE_FILE}"
        "${COMPILE_FLAGS}"
    )
endfunction()
