#!/bin/bash

# Installs the Cairo package, compiles and runs a Cairo source file.
# This test is run by the cairo-lang docker.

set -e

root_dir=$(pwd)
package_path=${root_dir}/cairo-lang-$(cat src/starkware/cairo/lang/VERSION).zip
cairo_source_path=${root_dir}/src/starkware/cairo/lang/package_test/main.cairo

tmpdir=$(mktemp -d)
cd ${tmpdir}

# Create a new virtual environment.
python3.9 -m venv venv

# Activate the environment.
source venv/bin/activate

# Install the Cairo package.
pip install ${package_path}

# Compile.
cairo-compile ${cairo_source_path} --output=main_compiled.json
res=$(cairo-run --program=main_compiled.json  --layout=small --print_output)

# Verify the result.
# The number below is pedersen(1, 2) (which is the expected output of main.cairo).
[[ "$res" == *"-1025514936890165471153863463586721648332140962090141185746964417035414175707"* ]]

cairo-reconstruct-traceback --version > /dev/null

# Test cairo-migrate.
cairo-migrate --help > /dev/null

# Test StarkNet compiler.
starknet-compile ${root_dir}/src/starkware/starknet/apps/amm_sample/amm_sample.cairo > /dev/null

# Test StarkNet CLI.
starknet --help > /dev/null
