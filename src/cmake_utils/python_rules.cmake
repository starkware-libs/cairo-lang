# CACHE INTERNAL makes the variables definitions available in every scope.
set(GEN_PY_LIB_EXECUTABLE ${CMAKE_CURRENT_LIST_DIR}/gen_py_lib.py CACHE INTERNAL "")
set(GEN_VENV_EXECUTABLE ${CMAKE_CURRENT_LIST_DIR}/gen_venv.py CACHE INTERNAL "")
set(GEN_PYTHON_EXE_EXECUTABLE ${CMAKE_CURRENT_LIST_DIR}/gen_python_exe.py CACHE INTERNAL "")
set(UNITE_LIBS_EXECUTABLE ${CMAKE_CURRENT_LIST_DIR}/unite_lib.py CACHE INTERNAL "")

set(PY_LIB_INFO_GLOBAL_DIR ${CMAKE_BINARY_DIR}/python_libs CACHE INTERNAL "")
function(get_lib_info_file OUTPUT_VARIABLE LIB)
  set(${OUTPUT_VARIABLE} ${PY_LIB_INFO_GLOBAL_DIR}/${LIB}.info PARENT_SCOPE)
endfunction()

add_custom_target(all_python_libs_dryrun)

# Creates a python library target.
# Caller should make this target depend on artifact targets (using add_dependencies())
# to force correct build order.
#
# Example usage:
#   python_lib(starkware_crypto_lib
#     FILES
#     starkware/__init__.py
#     ...
#     LIBS
#     starkware_storage_lib
#     pip_sympy
#   )
# For a test library:
#   python_lib(starkware_crypto_test_lib
#     FILES
#     starkware/crypto/my_test.py
#     ...
#     LIBS
#     pip_new_dependency_for_test_lib
#   )
function(python_lib LIB)
  # Parse arguments.
  set(options)
  set(oneValueArgs PREFIX)
  set(multiValueArgs FILES ARTIFACTS LIBS PY_EXE_DEPENDENCIES)
  cmake_parse_arguments(ARGS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  set(LIB_DIR_ROOT ${CMAKE_CURRENT_BINARY_DIR}/${LIB})

  if(ARGS_PREFIX)
    set(LIB_DIR ${LIB_DIR_ROOT}/${ARGS_PREFIX})
    set(ARGS_PREFIX "${ARGS_PREFIX}/")
  else()
    set(LIB_DIR ${LIB_DIR_ROOT})
  endif()

  set(LIB_FILES)
  foreach(FILE ${ARGS_FILES})
    list(APPEND LIB_FILES "${ARGS_PREFIX}${FILE}")
  endforeach()

  set(ALL_FILE_DEPS)

  # Copy files.
  copy_files(${LIB}_copy_files ${CMAKE_CURRENT_SOURCE_DIR} ${LIB_DIR} ${ARGS_FILES})
  get_target_property(COPY_STAMP ${LIB}_copy_files STAMP_FILE)
  list(APPEND ALL_FILE_DEPS ${COPY_STAMP})

  # Copy artifacts.
  foreach(ARTIFACT ${ARGS_ARTIFACTS})
    separate_arguments(ARTIFACT)
    list(GET ARTIFACT 0 ARTIFACT_SRC)
    list(GET ARTIFACT 1 ARTIFACT_DEST)

    add_custom_command(
      OUTPUT ${LIB_DIR}/${ARTIFACT_DEST}
      COMMAND ${CMAKE_COMMAND} -E copy
      ${ARTIFACT_SRC} ${LIB_DIR}/${ARTIFACT_DEST}
      DEPENDS ${ARTIFACT_SRC}
      COMMENT "Copying artifact ${ARTIFACT_SRC} to ${LIB_DIR}/${ARTIFACT_DEST}"
    )
    list(APPEND ALL_FILE_DEPS ${LIB_DIR}/${ARTIFACT_DEST})
    list(APPEND LIB_FILES ${ARGS_PREFIX}${ARTIFACT_DEST})
  endforeach()

  # Create a list of all dependencies regardless of python's version.
  set(UNITED_LIBS ${ARGS_LIBS})
  if("${UNITED_LIBS}" MATCHES ":")
    execute_process(
      COMMAND ${UNITE_LIBS_EXECUTABLE} ${UNITED_LIBS}
      OUTPUT_VARIABLE UNITED_LIBS
    )
  endif()
  separate_arguments(UNITED_LIBS)

  # Info target.
  set(DEP_INFO)
  foreach(DEP_LIB ${UNITED_LIBS} ${ARGS_PY_EXE_DEPENDENCIES})
    get_lib_info_file(DEP_INFO_FILE ${DEP_LIB})
    LIST(APPEND DEP_INFO ${DEP_INFO_FILE})
  endforeach()

  get_lib_info_file(INFO_FILE ${LIB})
  file(RELATIVE_PATH CMAKE_DIR ${CMAKE_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  set(GEN_PY_LIB_COMMAND
    ${GEN_PY_LIB_EXECUTABLE}
    --name ${LIB}
    --lib_dir ${LIB_DIR_ROOT}
    --files ${LIB_FILES}
    --lib_deps ${ARGS_LIBS}
    --py_exe_deps ${ARGS_PY_EXE_DEPENDENCIES}
    --cmake_dir ${CMAKE_DIR}
    --prefix ${ARGS_PREFIX}
  )
  add_custom_command(
    OUTPUT ${INFO_FILE}
    COMMAND ${GEN_PY_LIB_COMMAND} --output ${INFO_FILE}
    DEPENDS ${GEN_PY_LIB_EXECUTABLE} ${DEP_INFO} ${UNITED_LIBS}
      ${ARGS_PY_EXE_DEPENDENCIES} ${ALL_FILE_DEPS} ${LIB}_copy_files
  )
  add_custom_target(${LIB} ALL DEPENDS ${INFO_FILE})
  add_custom_command(
    OUTPUT ${INFO_FILE}.dryrun
    COMMAND ${GEN_PY_LIB_COMMAND} --output ${INFO_FILE}.dryrun
    DEPENDS ${GEN_PY_LIB_EXECUTABLE}
  )
  add_custom_target(${LIB}_dryrun DEPENDS ${INFO_FILE}.dryrun)
  add_dependencies(all_python_libs_dryrun ${LIB}_dryrun)
endfunction()

# Creates a virtual environment target.
# Usage: python_venv(venv_name PYTHON ${PYTHON_COMMAND} LIBS lib0 lib1 ...)
# Target properties:
# VENV_PYTHON: Full path to the vritual environment python executable.
# STAMP_FILE: when this file is generated, the virtual environment is ready to use.
function(python_venv VENV_NAME)
  # Parse arguments.
  set(options)
  set(oneValueArgs PYTHON)
  set(multiValueArgs LIBS)
  cmake_parse_arguments(ARGS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  # A directory with symlinks to files of other libraries.
  # This will be appended to .pth file.
  set(SITE_DIR ${CMAKE_CURRENT_BINARY_DIR}/${VENV_NAME}-site)
  set(VENV_DIR ${CMAKE_CURRENT_BINARY_DIR}/${VENV_NAME})
  get_lib_info_file(VENV_INFO_FILE ${VENV_NAME})

  set(DEP_INFO)
  foreach(DEP_LIB ${ARGS_LIBS})
    get_lib_info_file(DEP_INFO_FILE ${DEP_LIB})
    list(APPEND DEP_INFO ${DEP_INFO_FILE})
  endforeach()

  add_custom_command(
    OUTPUT ${VENV_INFO_FILE}
    COMMAND ${GEN_VENV_EXECUTABLE}
      --name ${VENV_NAME}
      --libs ${ARGS_LIBS}
      --python ${ARGS_PYTHON}
      --site_dir ${SITE_DIR}
      --venv_dir ${VENV_DIR}
      --info_dir ${PY_LIB_INFO_GLOBAL_DIR}
    DEPENDS ${GEN_VENV_EXECUTABLE} ${DEP_INFO} ${ARGS_LIBS}
  )

  # Create target.
  add_custom_target(${VENV_NAME} ALL
    DEPENDS ${VENV_INFO_FILE}
  )

  # Target properties.
  set_target_properties(${VENV_NAME} PROPERTIES
    VENV_PYTHON ${VENV_DIR}/bin/python
    STAMP_FILE ${VENV_INFO_FILE}
  )
endfunction()

# Creates a python executable target, based on a specific python module, which runs inside a
# given python virtual environment.
# Example usage:
#   python_exe(hello_world
#     VENV hello_world_venv
#     MODULE hello_world
#     ARGS -a
#   )
function(python_exe EXE_NAME)
  # Parse arguments.
  set(options)
  set(oneValueArgs VENV MODULE ARGS WORKING_DIR ENVIRONMENT_VARS)
  set(multiValueArgs)
  cmake_parse_arguments(ARGS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  get_lib_info_file(VENV_INFO_FILE ${ARGS_VENV})
  get_lib_info_file(INFO_FILE ${EXE_NAME})
  add_to_executables_list(${EXE_NAME})

  # Create a runner script.
  set(EXECUTABLE_PATH ${CMAKE_CURRENT_BINARY_DIR}/${EXE_NAME})

  # This command generates both INFO_FILE and EXE_NAME.
  # However, we cannot list EXE_NAME as an output, since it clashes with the custom target below.
  add_custom_command(
    OUTPUT ${INFO_FILE}
    COMMAND ${GEN_PYTHON_EXE_EXECUTABLE}
      --name ${EXE_NAME}
      --exe_path ${EXECUTABLE_PATH}
      --venv ${ARGS_VENV}
      --module ${ARGS_MODULE}
      "--args=${ARGS_ARGS}"
      --info_dir ${PY_LIB_INFO_GLOBAL_DIR}
      --cmake_binary_dir ${CMAKE_BINARY_DIR}
      "--working_dir=${ARGS_WORKING_DIR}"
      "--environment_variables=${ARGS_ENVIRONMENT_VARS}"
    DEPENDS ${GEN_PYTHON_EXE_EXECUTABLE} ${ARGS_VENV} ${VENV_INFO_FILE}
  )

  # Create target.
  add_custom_target(${EXE_NAME} ALL
    DEPENDS ${ARGS_VENV} ${INFO_FILE}
  )
endfunction()

function(python_test TEST_NAME)
  # Parse arguments.
  set(options NO_CODE_COVERAGE)
  set(oneValueArgs VENV TESTED_MODULES TEST_ARGS ENVIRONMENT_VARS)
  set(multiValueArgs)
  cmake_parse_arguments(ARGS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  # If code coverage is enabled, and the target is run as part of the nightly run, need to add
  # command line options + an environment variable.
  set(COVERAGE_ARGS "")
  if(NOT ARGS_NO_CODE_COVERAGE AND ("$ENV{NIGHTLY_TEST}" EQUAL "1"))
    # Set COVERAGE_DEBUG environment variable for debugging coverage-related failures, as suggested
    # here: https://github.com/pytest-dev/pytest-cov/issues/237.
    set(ENV{COVERAGE_DEBUG} "process,config")
    set(COVERAGE_ARGS "--cov-report html:{VENV_SITE_DIR}/coverage_py_html \
      --cov {VENV_SITE_DIR}/${ARGS_TESTED_MODULES}"
    )
    string(REPLACE "/" "." COVERAGE_FILE_SUFFIX "${ARGS_TESTED_MODULES}")
    string(APPEND ARGS_ENVIRONMENT_VARS " COVERAGE_FILE=.coverage.${COVERAGE_FILE_SUFFIX}")
  endif()

  python_exe(${TEST_NAME}
    VENV ${ARGS_VENV}
    MODULE pytest
    ARGS "${COVERAGE_ARGS} {VENV_SITE_DIR}/${ARGS_TESTED_MODULES} ${ARGS_TEST_ARGS}"
    WORKING_DIR ${CMAKE_BINARY_DIR}
    ENVIRONMENT_VARS ${ARGS_ENVIRONMENT_VARS}
  )

  add_test(
    NAME ${TEST_NAME}
    COMMAND ${CMAKE_CURRENT_BINARY_DIR}/${TEST_NAME}
  )
endfunction()

function(full_python_test TEST_NAME)
  # Parse arguments.
  set(options NO_CODE_COVERAGE)
  set(oneValueArgs TESTED_MODULES TEST_ARGS PYTHON ENVIRONMENT_VARS)
  set(multiValueArgs LIBS ARTIFACTS PY_EXE_DEPENDENCIES)
  cmake_parse_arguments(ARGS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  # If code coverage is suppressed, the option needs to be passed to the python_exe macro.
  # Otherwise, need to add the pytest-cov dependency.
  set(CODE_COVERAGE_SUPPRESSION_FLAG)
  if(ARGS_NO_CODE_COVERAGE OR NOT ("$ENV{NIGHTLY_TEST}" EQUAL "1"))
    set(CODE_COVERAGE_SUPPRESSION_FLAG NO_CODE_COVERAGE)
  else()
    list(APPEND ARGS_LIBS "pip_pytest_cov")
  endif()

  # Use a 3rd-party Python debugger (instead of `pdb`).
  #
  # Usage: Override both args below before CMake imports this file.
  # The contents of the variables should be as follows:
  #
  #     PYTHON_DEBUGGER_LIB: the name of the python_lib for the debugger package.
  #         format: "pip_<lib_name>" # For more on this format, see the definition
  #                                    of `python_lib` above.
  #     PYTHON_BREAKPOINT_HANDLER: the cmd that triggers the debugger
  #                                (will be run when `breakpoint()` is called).
  #         format: "PYTHONBREAKPOINT=<debugger_start_command>"
  #
  # Example (for the package `ipdb`):
  #
  #    PYTHON_DEBUGGER_LIB="pip_ipdb"
  #    PYTHON_BREAKPOINT_HANDLER="PYTHONBREAKPOINT=ipdb.set_trace"
  list(APPEND ARGS_LIBS ${PYTHON_DEBUGGER_LIB})
  list(APPEND ARGS_ENVIRONMENT_VARS ${PYTHON_BREAKPOINT_HANDLER})

  python_lib(${TEST_NAME}_lib
    ${ARGS_UNPARSED_ARGUMENTS}
    LIBS ${ARGS_LIBS}
    ARTIFACTS ${ARGS_ARTIFACTS}
    PY_EXE_DEPENDENCIES ${ARGS_PY_EXE_DEPENDENCIES}
  )
  python_venv(${TEST_NAME}_venv
    PYTHON ${ARGS_PYTHON}
    LIBS ${TEST_NAME}_lib
  )
  python_test(${TEST_NAME}
    VENV ${TEST_NAME}_venv
    TESTED_MODULES ${ARGS_TESTED_MODULES}
    TEST_ARGS ${ARGS_TEST_ARGS}
    ENVIRONMENT_VARS ${ARGS_ENVIRONMENT_VARS}
    ${CODE_COVERAGE_SUPPRESSION_FLAG}
  )
endfunction()
