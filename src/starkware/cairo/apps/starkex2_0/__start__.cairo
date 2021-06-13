# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

# Add the initial code that was removed from the compiler in order to get the correct program hash.
# This code is not required for the execution of the program using the bootloader.
__start__:
call rel 748
jmp rel 0
