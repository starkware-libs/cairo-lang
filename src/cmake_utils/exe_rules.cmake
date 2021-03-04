include_guard(GLOBAL)

# These rules automatically collect all executables added in cmake to a list of executables.
# By hooking the existing add_exectuable() rule, users do not have to do anything to get their
# executable listed.
# Utils to collect all executable paths by target name.
set(EXECUTABLES_FILENAME ${CMAKE_BINARY_DIR}/executables.txt)
file(WRITE ${EXECUTABLES_FILENAME})
function(add_to_executables_list TARGET)
  file(APPEND ${EXECUTABLES_FILENAME} "${TARGET} ${CMAKE_CURRENT_BINARY_DIR}\n")
endfunction(add_to_executables_list)

# Hook add_executable, to make a list of executables by target.
function(add_executable TARGET)
   # Call the original function
   _add_executable(${TARGET} ${ARGN})
   add_to_executables_list(${TARGET})
endfunction(add_executable TARGET)
