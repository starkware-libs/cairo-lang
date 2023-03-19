set(CAIRO_COMPILER_DUMMY_FILE "${CMAKE_CURRENT_BINARY_DIR}/cairo_compiler_v1")
set(CAIRO_COMPILER_DIR "${CMAKE_CURRENT_BINARY_DIR}/cairo")

set(CAIRO_COMPILER_FILES
    "${CAIRO_COMPILER_DIR}/bin/cairo-compile"
    "${CAIRO_COMPILER_DIR}/bin/cairo-format"
    "${CAIRO_COMPILER_DIR}/bin/cairo-language-server"
    "${CAIRO_COMPILER_DIR}/bin/cairo-run"
    "${CAIRO_COMPILER_DIR}/bin/cairo-test"
    "${CAIRO_COMPILER_DIR}/bin/sierra-compile"
    "${CAIRO_COMPILER_DIR}/bin/starknet-compile"
    "${CAIRO_COMPILER_DIR}/bin/starknet-sierra-compile"
    "${CAIRO_COMPILER_DIR}/corelib/cairo_project.toml"
    "${CAIRO_COMPILER_DIR}/corelib/Scarb.toml"
    "${CAIRO_COMPILER_DIR}/corelib/src/array.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/box.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/clone.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/debug.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/dict.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/ec.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/ecdsa.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/gas.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/hash.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/integer.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/internal.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/lib.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/nullable.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/option.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/result.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/serde.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/class_hash.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/contract_address.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/info.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/storage_access.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/syscalls.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/testing.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/test.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/testing.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/traits.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/zeroable.cairo"
)

set(CAIRO_COMPILER_ARTIFACTS
    "${CAIRO_COMPILER_DIR}/bin/cairo-compile bin/cairo-compile"
    "${CAIRO_COMPILER_DIR}/bin/cairo-format bin/cairo-format"
    "${CAIRO_COMPILER_DIR}/bin/cairo-language-server bin/cairo-language-server"
    "${CAIRO_COMPILER_DIR}/bin/cairo-run bin/cairo-run"
    "${CAIRO_COMPILER_DIR}/bin/cairo-test bin/cairo-test"
    "${CAIRO_COMPILER_DIR}/bin/sierra-compile bin/sierra-compile"
    "${CAIRO_COMPILER_DIR}/bin/starknet-compile bin/starknet-compile"
    "${CAIRO_COMPILER_DIR}/bin/starknet-sierra-compile bin/starknet-sierra-compile"
    "${CAIRO_COMPILER_DIR}/corelib/cairo_project.toml corelib/cairo_project.toml"
    "${CAIRO_COMPILER_DIR}/corelib/Scarb.toml corelib/Scarb.toml"
    "${CAIRO_COMPILER_DIR}/corelib/src/array.cairo corelib/src/array.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/box.cairo corelib/src/box.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/clone.cairo corelib/src/clone.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/debug.cairo corelib/src/debug.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/dict.cairo corelib/src/dict.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/ec.cairo corelib/src/ec.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/ecdsa.cairo corelib/src/ecdsa.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/gas.cairo corelib/src/gas.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/hash.cairo corelib/src/hash.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/integer.cairo corelib/src/integer.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/internal.cairo corelib/src/internal.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/lib.cairo corelib/src/lib.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/nullable.cairo corelib/src/nullable.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/option.cairo corelib/src/option.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/result.cairo corelib/src/result.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/serde.cairo corelib/src/serde.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet.cairo corelib/src/starknet.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/class_hash.cairo corelib/src/starknet/class_hash.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/contract_address.cairo corelib/src/starknet/contract_address.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/info.cairo corelib/src/starknet/info.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/storage_access.cairo corelib/src/starknet/storage_access.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/syscalls.cairo corelib/src/starknet/syscalls.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/starknet/testing.cairo corelib/src/starknet/testing.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/test.cairo corelib/src/test.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/testing.cairo corelib/src/testing.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/traits.cairo corelib/src/traits.cairo"
    "${CAIRO_COMPILER_DIR}/corelib/src/zeroable.cairo corelib/src/zeroable.cairo"
)

add_custom_command(
    OUTPUT "${CAIRO_COMPILER_DUMMY_FILE}" "${CAIRO_COMPILER_FILES}"
    COMMAND curl -Lo release-x86_64-unknown-linux-musl.tar.gz https://github.com/starkware-libs/cairo/releases/download/v1.0.0-alpha.6/release-x86_64-unknown-linux-musl.tar.gz
    COMMAND tar -xf release-x86_64-unknown-linux-musl.tar.gz
    COMMAND touch "${CAIRO_COMPILER_DUMMY_FILE}"
    COMMENT "Downloading cairo compiler."
)

add_custom_target(get_cairo_compiler DEPENDS ${CAIRO_COMPILER_DUMMY_FILE})

python_lib(starknet_compile_v1_lib
    PREFIX starkware/starknet/compiler/v1

    FILES
    compile.py
    mainnet_libfuncs.json
    testnet_libfuncs.json
    testnet2_libfuncs.json

    ARTIFACTS
    "${CAIRO_COMPILER_ARTIFACTS}"

    LIBS
    starknet_definitions_lib
    starkware_error_handling_lib
)

add_dependencies(starknet_compile_v1_lib get_cairo_compiler)
