# Note: STAMP_FILE is a dummy output file for a target that holds all of the reqeuired file level
# dependencies of the target. If you have a custom command that needs a dependency target to run
# before, it should depend on the target and the stamp file.

# Create a target for a python library from a pip requirement REQ.
# REQ is a pip requirement line. For example, abcd==1.2.3, or requests>2.1 .
function(python_pip TARGET)
  # Parse arguments.
  set(options)
  set(oneValueArgs)
  set(multiValueArgs VERSIONS LIBS)
  cmake_parse_arguments(ARGS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  # Create a list of all dependencies regardless of python's version.
  set(UNITED_LIBS ${ARGS_LIBS})
  if("${UNITED_LIBS}" MATCHES ":")
    execute_process(
      COMMAND ${UNITE_LIBS_EXECUTABLE} ${UNITED_LIBS}
      OUTPUT_VARIABLE UNITED_LIBS
    )
  endif()
  separate_arguments(UNITED_LIBS)

  set(ALL_STAMPS)
  set(ALL_LIB_DIRS)
  foreach(VERSION ${ARGS_VERSIONS})
    separate_arguments(VERSION)
    list(GET VERSION 0 INTERPRETER)
    list(GET VERSION 1 REQ)

    set(LIB_DIR ${CMAKE_BINARY_DIR}/python_pip/${INTERPRETER}/${TARGET})
    set(DOWNLOAD_DIR ${CMAKE_BINARY_DIR}/python_pip_downloads/${INTERPRETER}/${TARGET})
    # Adding REQ here makes sure a different version will rebuild target.
    # The filename will have '==' in it.
    set(STAMP_FILE ${CMAKE_BINARY_DIR}/python_pip/${TARGET}_${INTERPRETER}_${REQ}.stamp)

    # Creating library directory.
    if (${REQ} MATCHES "\\+local$")
        string(REPLACE "==" "-" PACKAGE_NAME ${REQ})
        set(ZIP_FILE "${PROJECT_SOURCE_DIR}/${PACKAGE_NAME}.zip")
        add_custom_command(
          OUTPUT ${STAMP_FILE}
          COMMENT "Building ${REQ} from a local copy."
          COMMAND rm -rf ${LIB_DIR}/*
          COMMAND unzip ${ZIP_FILE} -d ${LIB_DIR} > /dev/null
          COMMAND mv ${LIB_DIR}/${PACKAGE_NAME}/* ${LIB_DIR}/
          COMMAND rm -rf ${LIB_DIR}/${PACKAGE_NAME}/
          COMMAND ${CMAKE_COMMAND} -E touch ${STAMP_FILE}
          DEPENDS ${ZIP_FILE}
        )
    else()
        add_custom_command(
          OUTPUT ${STAMP_FILE}
          # Download or build wheel.
          COMMENT "Building wheel ${REQ} for ${INTERPRETER}"
          COMMAND ${CMAKE_COMMAND} -E make_directory ${LIB_DIR}
          COMMAND ${CMAKE_COMMAND} -E make_directory ${DOWNLOAD_DIR}
          COMMAND
            ${INTERPRETER} -m pip wheel --no-deps -w ${DOWNLOAD_DIR}/ ${REQ} ${PIP_INSTALL_ARGS_${INTERPRETER}}
          # Extract wheel.
          COMMAND cd ${LIB_DIR} && ${CMAKE_COMMAND} -E tar xzf ${DOWNLOAD_DIR}/*.whl
          # Some wheels may put their files at /{name}-{version}.data/(pure|plat)lib/, instead of
          # under the root directory. See https://www.python.org/dev/peps/pep-0427/#id24.
          # Copy the files from there. Suppress errors, which happen most of the times when this
          # subdirectory does not exist.
          COMMAND cp -r ${LIB_DIR}/*.data/*lib/* ${LIB_DIR}/ > /dev/null 2>&1 || true
          # Cleanup download.
          COMMAND ${CMAKE_COMMAND} -E remove_directory ${DOWNLOAD_DIR}
          # Timestamp.
          COMMAND ${CMAKE_COMMAND} -E touch ${STAMP_FILE}
        )
    endif()

    list(APPEND ALL_STAMPS ${STAMP_FILE})
    list(APPEND ALL_LIB_DIRS "${INTERPRETER}:${LIB_DIR}")
  endforeach()

  # Info target.
  set(DEP_INFO)
  foreach(DEP_LIB ${UNITED_LIBS})
    get_lib_info_file(DEP_INFO_FILE ${DEP_LIB})
    set(DEP_INFO ${DEP_INFO} ${DEP_INFO_FILE})
  endforeach()

  get_lib_info_file(INFO_FILE ${TARGET})
  add_custom_command(
    OUTPUT ${INFO_FILE}
    COMMAND ${GEN_PY_LIB_EXECUTABLE}
      --name ${TARGET}
      --lib_dir ${ALL_LIB_DIRS}
      --import_paths ${ALL_LIB_DIRS}
      --lib_deps ${ARGS_LIBS}
      --output ${INFO_FILE}
      --py_exe_deps
    DEPENDS ${GEN_PY_LIB_EXECUTABLE} ${DEP_INFO} ${UNITED_LIBS} ${ALL_STAMPS}
  )

  add_custom_target(${TARGET} ALL
    DEPENDS ${INFO_FILE}
  )
endfunction()


# Creates all pip library targets from a given pipdeptree json file.
# TARGET is a name to represent this dependency tree.
# DEPS_FILE is a json file created by pipdeptree (or lock_reqs.py).
set(PIP_GEN_EXECUTABLE ${CMAKE_CURRENT_LIST_DIR}/gen_pip_cmake.py)
function(python_get_pip_deps TARGET)
  set(CMAKE_FILE "${CMAKE_CURRENT_BINARY_DIR}/${TARGET}_generated_rules.cmake")

  # Create a list of all dependency files.
  set(UNITED_DEP_FILES ${ARGN})
  if("${UNITED_DEP_FILES}" MATCHES ":")
    execute_process(
      COMMAND ${UNITE_LIBS_EXECUTABLE} ${UNITED_DEP_FILES}
      OUTPUT_VARIABLE UNITED_DEP_FILES
    )
  endif()
  separate_arguments(UNITED_DEP_FILES)

  # Add as a reconfigure dependency, so that CMake will reconfigure on change.
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${UNITED_DEP_FILES})

  # Generate cmake file on configure.
  execute_process(
      COMMAND ${PIP_GEN_EXECUTABLE}
        --interpreter_deps ${ARGN}
        --output ${CMAKE_FILE}
  )
  include(${CMAKE_FILE})
endfunction()
