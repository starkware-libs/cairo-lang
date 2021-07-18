cmake_minimum_required (VERSION 3.5)

project(CairoLang VERSION 0.1.0)
include(CTest)

enable_testing()

if (NOT DEFINED CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug)
endif()

# Python library macro.
find_program(PYTHON "python3")

include("src/cmake_utils/cmake_rules.cmake")
include("src/starkware/cairo/lang/cairo_cmake_rules.cmake")

# Repos needs to be first as it defines macros that are needed by src.
add_subdirectory(src)
