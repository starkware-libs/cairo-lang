load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_binary")

def starknet_contract_v0(
        name,
        compiled_program_name,
        cairo_compile_exe = "//src/starkware/starknet/compiler:starknet_compile_exe",
        **kwargs):
    cairo_binary(
        name = name,
        abi = "%s_abi.json" % name,
        compiled_program_name = compiled_program_name,
        cairo_compile_exe = cairo_compile_exe,
        **kwargs
    )
