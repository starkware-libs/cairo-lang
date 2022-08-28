# Generic logic for compiling Cairo or StarkNet contracts.
# See cairo_compile for usage example.
function(cairo_compile_base TARGET_NAME COMPILER_EXE COMPILED_PROGRAM_NAME SOURCE_FILE
    COMPILE_FLAGS)
    # Choose a file name for the Cairo dependencies of the compiled file.
    set(COMPILE_DEPENDENCY_FILE
        "${CMAKE_CURRENT_BINARY_DIR}/${TARGET_NAME}_compile_dependencies.cmake")
    # If this is the first build, create an empty dependency file (this file will be overriden when
    # cairo-compile is executed with the actual dependencies, using the --cairo_dependencies flag).
    if(NOT EXISTS ${COMPILE_DEPENDENCY_FILE})
      file(WRITE ${COMPILE_DEPENDENCY_FILE} "")
    endif()
    # The following include() will populate the DEPENDENCIES variable with the Cairo files.
    include(${COMPILE_DEPENDENCY_FILE})

    get_filename_component(COMPILER_EXE_TARGET ${COMPILER_EXE} NAME)
    separate_arguments(COMPILE_FLAGS)
    add_custom_command(
        OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/${COMPILED_PROGRAM_NAME}"
        COMMAND ${COMPILER_EXE}
        "${CMAKE_CURRENT_SOURCE_DIR}/${SOURCE_FILE}"
        "--output=${CMAKE_CURRENT_BINARY_DIR}/${COMPILED_PROGRAM_NAME}"
        "--prime=3618502788666131213697322783095070105623107215331596699973092056135872020481"
        "--cairo_path=${CMAKE_SOURCE_DIR}/src"
        "--cairo_dependencies=${COMPILE_DEPENDENCY_FILE}"
        ${COMPILE_FLAGS}
        DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${SOURCE_FILE}"
        ${COMPILE_DEPENDENCY_FILE} ${DEPENDENCIES} ${COMPILER_EXE_TARGET} ${COMPILER_EXE}
    COMMENT "Compiling ${CMAKE_CURRENT_SOURCE_DIR}/${SOURCE_FILE}"
    )

    add_custom_target(${TARGET_NAME}
        ALL
        DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/${COMPILED_PROGRAM_NAME}"
    )
endfunction()

# Compiles a Cairo program.
# Usage example:
#   cairo_compile(mytarget main_compiled.json main.cairo "--debug_info_with_source")
function(cairo_compile TARGET_NAME COMPILED_PROGRAM_NAME SOURCE_FILE COMPILE_FLAGS)
    cairo_compile_base(
        ${TARGET_NAME}
        "${CMAKE_BINARY_DIR}/src/starkware/cairo/lang/compiler/cairo_compile_exe"
        "${COMPILED_PROGRAM_NAME}"
        "${SOURCE_FILE}"
        "${COMPILE_FLAGS}"
    )
endfunction()


# Compiles and runs a Cairo file.
# ARTIFACTS is a ';'-separated list that may contain the following artifacts:
#   * trace
#   * public_input
function(cairo_compile_run TARGET_NAME FILENAME STEPS ARTIFACTS COMPILE_FLAGS RUN_FLAGS)
    get_lib_info_file(STAMP_FILE cairo_lang_venv)

    set(ARTIFACT_LIST ${ARTIFACTS})

    # Choose a file name for the python dependencies of cairo-run.
    set(RUN_DEPENDENCY_FILE "${CMAKE_CURRENT_BINARY_DIR}/${FILENAME}_run_dependencies.cmake")
    # If this is the first build, create an empty dependency file (this file will be overriden when
    # cairo-run is executed with the actual dependencies, using the --python_dependencies flag).
    if(NOT EXISTS ${RUN_DEPENDENCY_FILE})
      file(WRITE ${RUN_DEPENDENCY_FILE} "")
    endif()
    # The following include() will populate the DEPENDENCIES variable with the python modules used
    # by cairo-compile and cairo-run.
    include(${RUN_DEPENDENCY_FILE})

    if ("trace" IN_LIST ARTIFACT_LIST)
        set(MEMORY_FILE "${CMAKE_CURRENT_BINARY_DIR}/${FILENAME}_memory.bin")
        set(TRACE_FILE "${CMAKE_CURRENT_BINARY_DIR}/${FILENAME}_trace.bin")
        set(TRACE_HEADER "${TRACE_FILE}.h")
        set(MEMORY_HEADER "${MEMORY_FILE}.h")
        set(GENERATE_TRACE "--trace_file=${TRACE_FILE}")
        set(GENERATE_MEMORY "--memory_file=${MEMORY_FILE}")
    endif()
    if ("public_input" IN_LIST ARTIFACT_LIST)
        set(PUBLIC_INPUT_FILE "${CMAKE_CURRENT_BINARY_DIR}/${FILENAME}_public_input.json")
        set(PUBLIC_INPUT_HEADER "${PUBLIC_INPUT_FILE}.h")
        set(GENERATE_PUBLIC_INPUT "--air_public_input=${PUBLIC_INPUT_FILE}")
    endif()

    cairo_compile(
        "${TARGET_NAME}_compile"
        "${TARGET_NAME}_compiled.json"
        "${FILENAME}.cairo"
        "${COMPILE_FLAGS}")

    separate_arguments(RUN_FLAGS)

    add_custom_command(
        OUTPUT "${MEMORY_FILE}" "${TRACE_FILE}" "${PUBLIC_INPUT_FILE}"
        COMMAND "${CMAKE_BINARY_DIR}/src/starkware/cairo/lang/cairo_lang_venv/bin/python"
        "-m" "starkware.cairo.lang.vm.cairo_run"
        "--program=${CMAKE_CURRENT_BINARY_DIR}/${TARGET_NAME}_compiled.json"
        "--steps=${STEPS}"
        "--python_dependencies=${RUN_DEPENDENCY_FILE}"
        "--proof_mode"
        ${RUN_FLAGS}
        "${GENERATE_MEMORY}"
        "${GENERATE_TRACE}"
        "${GENERATE_PUBLIC_INPUT}"
        DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${FILENAME}.cairo"
            "${TARGET_NAME}_compiled.json"
            ${RUN_DEPENDENCY_FILE} ${DEPENDENCIES} cairo_lang_venv ${VENV_STAMP}
        COMMENT "Executing ${CMAKE_CURRENT_SOURCE_DIR}/${FILENAME}.cairo"
    )
    if ("trace" IN_LIST ARTIFACT_LIST)
        generate_cpp_resource(
            ${TRACE_FILE}
            ${TRACE_HEADER}
            ${FILENAME}_trace
        )
        generate_cpp_resource(
            ${MEMORY_FILE}
            ${MEMORY_HEADER}
            ${FILENAME}_memory
        )
    endif()
    if ("public_input" IN_LIST ARTIFACT_LIST)
        generate_cpp_resource(
            ${PUBLIC_INPUT_FILE}
            ${PUBLIC_INPUT_HEADER}
            ${FILENAME}_public_input
        )
    endif()

    add_custom_target(${TARGET_NAME}
        DEPENDS "${TRACE_HEADER}" "${MEMORY_HEADER}" "${PUBLIC_INPUT_HEADER}"
    )
endfunction(cairo_compile_run)
