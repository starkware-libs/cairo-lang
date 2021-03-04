include("${CMAKE_SOURCE_DIR}/src/cmake_utils/exe_rules.cmake")
include("${CMAKE_SOURCE_DIR}/src/cmake_utils/copy_rules.cmake")
include("${CMAKE_SOURCE_DIR}/src/cmake_utils/python_rules.cmake")
include("${CMAKE_SOURCE_DIR}/src/cmake_utils/pip_rules.cmake")
python_get_pip_deps(main_reqs
  python3.7:${CMAKE_SOURCE_DIR}/scripts/requirements-deps.json
  ${ADDITIONAL_PIP_DEPS}
)
