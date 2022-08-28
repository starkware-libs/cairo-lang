cmake_minimum_required (VERSION 3.22)

set (PYTHON_COMMAND python3.9)

project(CairoLang VERSION 0.1.0)
include(CTest)

enable_testing()

if (NOT DEFINED CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug)
endif()

# Python library macro.
find_program(PYTHON "python3")

include("src/cmake_utils/cmake_rules.cmake")
include("src/cmake_utils/solidity_rules.cmake")
include("src/starkware/cairo/lang/cairo_cmake_rules.cmake")
include("src/starkware/starknet/compiler/starknet_cmake_rules.cmake")

add_subdirectory(src)
