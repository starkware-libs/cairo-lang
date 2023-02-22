set(PROGRAM_ARTIFACTS)
add_custom_target(cairo_verifier_program_all_layouts)

function(cairo_verifier_layout LAYOUT_NAME)
    cairo_compile(cairo_verifier_program_${LAYOUT_NAME}
        cairo_verifier_compiled_${LAYOUT_NAME}.json
        layouts/${LAYOUT_NAME}/cairo_verifier.cairo
        "--no_debug_info --proof_mode"
    )
    set(
        PROGRAM_ARTIFACTS
        ${PROGRAM_ARTIFACTS}
        "${CMAKE_CURRENT_BINARY_DIR}/cairo_verifier_compiled_${LAYOUT_NAME}.json cairo_verifier_compiled_${LAYOUT_NAME}.json"
        PARENT_SCOPE
    )
    add_dependencies(cairo_verifier_program_all_layouts cairo_verifier_program_${LAYOUT_NAME})
endfunction()

cairo_verifier_layout(all_cairo)

add_subdirectory(layouts/all_cairo)
