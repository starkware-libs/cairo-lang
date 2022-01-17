set(GEN_SOLIDITY_ENV_EXE ${CMAKE_BINARY_DIR}/src/cmake_utils/gen_solidity_exe CACHE INTERNAL "")

# Creates a solidity environment target.
# Usage: solidity_env(venv_name LIBS lib0 lib1 ...)
function(solidity_env ENV_NAME)
  # Parse arguments.
  set(options)
  set(oneValueArgs)
  set(multiValueArgs CONTRACTS LIBS)
  cmake_parse_arguments(ARGS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  # A directory with symlinks to files of other libraries.
  set(ENV_DIR ${CMAKE_CURRENT_BINARY_DIR}/${ENV_NAME})
  get_lib_info_file(ENV_INFO_FILE ${ENV_NAME})

  set(DEP_INFO)
  foreach(DEP_LIB ${ARGS_LIBS})
    get_lib_info_file(DEP_INFO_FILE ${DEP_LIB})
    set(DEP_INFO ${DEP_INFO} ${DEP_INFO_FILE})
  endforeach()

  add_custom_command(
    OUTPUT ${ENV_INFO_FILE}
    COMMAND ${GEN_SOLIDITY_ENV_EXE}
      --name ${ENV_NAME}
      --libs ${ARGS_LIBS}
      --env_dir ${ENV_DIR}
      --info_dir ${PY_LIB_INFO_GLOBAL_DIR}
    DEPENDS gen_solidity_exe ${GEN_SOLIDITY_ENV_EXE} ${DEP_INFO} ${ARGS_LIBS}
  )

  # Add contract file targets.
  foreach(CONTRACT ${ARGS_CONTRACTS})
    set(OUTPUT_FILENAME ${CMAKE_CURRENT_BINARY_DIR}/${CONTRACT}.json)
    add_custom_command(
      OUTPUT ${OUTPUT_FILENAME}
      COMMAND ${CMAKE_COMMAND} -E copy
        ${ENV_DIR}/artifacts/${CONTRACT}.json
        ${OUTPUT_FILENAME}
      DEPENDS ${ENV_INFO_FILE}
      COMMENT "Copying contract ${CONTRACT}"
    )
    set(OUTPUT_FILES ${OUTPUT_FILES} ${OUTPUT_FILENAME})
  endforeach(CONTRACT)

  # Create target.
  add_custom_target(${ENV_NAME} ALL
    DEPENDS ${ENV_INFO_FILE} ${OUTPUT_FILES}
  )
endfunction()
