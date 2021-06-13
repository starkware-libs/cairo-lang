import argparse
import os

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.python.utils import get_source_dir_path
from starkware.starknet.security.secure_hints import HintsWhitelist

"""
Fix using the starknet_hints_latest_whitelist_fix executable.
"""


CAIRO_FILE = os.path.join(os.path.dirname(__file__), 'starknet_common.cairo')


def run(fix: bool):
    program = compile_cairo_files(files=[CAIRO_FILE], prime=DEFAULT_PRIME)
    filename = get_source_dir_path('src/starkware/starknet/security/whitelists/latest.json')
    whitelist = HintsWhitelist.from_program(program)
    if fix:
        data = HintsWhitelist.Schema().dumps(whitelist, indent=4, sort_keys=True)
        with open(filename, 'w') as fp:
            fp.write(data)
            fp.write('\n')
        return

    expected_whitelist = HintsWhitelist.from_file(filename)
    assert whitelist == expected_whitelist


def test_latest_whitelist():
    run(fix=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Checks/fixes the latest StarkNet hint whitelist file.')
    parser.add_argument('--fix', action='store_true', help='Fix the latest whitelist file.')
    args = parser.parse_args()
    run(fix=args.fix)
