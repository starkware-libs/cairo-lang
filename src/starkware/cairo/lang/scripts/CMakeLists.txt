python_lib(cairo_script_lib
    PREFIX starkware/cairo/lang/scripts
    FILES
    cairo-compile
    cairo-format
    cairo-hash-program
    cairo-run
    cairo-sharp

    LIBS
    cairo_compile_lib
    cairo_hash_program_lib
    cairo_run_lib
    sharp_client_lib
)
