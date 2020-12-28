cmake_minimum_required (VERSION 3.5)

project(CairoLang VERSION 0.1.0)
include(CTest)

enable_testing()

if (NOT DEFINED CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug)
endif()

# Python library macro.
find_program(PYTHON "python3")

include("repos/starkware-public/cmake_utils/exe_rules.cmake")
include("repos/starkware-public/cmake_utils/python_rules.cmake")
include("repos/starkware-public/cmake_utils/pip_rules.cmake")
python_get_pip_deps(main_reqs
    python3.7:${CMAKE_SOURCE_DIR}/scripts/requirements-deps.json
)

# Repos needs to be first as it defines macros that are needed by src.
add_subdirectory(repos)
add_subdirectory(src)
