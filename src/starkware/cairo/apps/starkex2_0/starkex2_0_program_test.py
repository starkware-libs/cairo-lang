# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

import os
import subprocess
import tempfile

from starkware.python.utils import get_build_dir_path


def test_program_hash():
    """
    Tests that the hash of the compiled Cairo program is identical to the one used in the
    StarkEx2.0 system.
    """
    DIR = os.path.dirname(__file__)
    CAIRO_PATH = os.path.join(DIR, '../../../..')
    PROGRAM_MAIN_FILE = os.path.join(DIR, 'main.cairo')
    CAIRO_COMPILE_EXE = get_build_dir_path('src/starkware/cairo/lang/compiler/cairo_compile_exe')
    CAIRO_HASH_PROGRAM_EXE = get_build_dir_path(
        'src/starkware/cairo/bootloader/cairo_hash_program_exe')

    with tempfile.NamedTemporaryFile() as compiled_program:
        # Compile the program.
        subprocess.check_call([
            f'{CAIRO_COMPILE_EXE}',
            PROGRAM_MAIN_FILE,
            f'--output={compiled_program.name}',
            f'--cairo_path={CAIRO_PATH}',
            '--no_opt_unused_functions',
        ])
        program_hash = subprocess.check_output([
            f'{CAIRO_HASH_PROGRAM_EXE}',
            f'--program={compiled_program.name}',
        ]).decode('ascii').strip()

    # NOTE: The following is the hash of the deployed program in the StarkEx2.0 system.
    # It should not be modified.
    assert program_hash == '0x15bd9af059b37335cf934461ce167400eec0ef18605193a25fc4bc6f661984a'
