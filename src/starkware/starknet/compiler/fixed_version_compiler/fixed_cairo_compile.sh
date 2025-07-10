#!/usr/bin/env bash

# 1. Gets the location of python from the first argument.
# 2. Creates a virtual python environment and installs cairo-lang==0.14.0a1.
# 3. Runs the cairo-compile binary on the rest of the script inputs.

set -euo pipefail

PYTHON="$1"
CAIRO_LANG="$2"
shift 2
echo "[INFO] Found Python at $PYTHON, using cairo-lang version $CAIRO_LANG" >&2

VENV_DIR=$(mktemp -d -p .)
echo "[INFO] Creating venv at: $VENV_DIR" >&2
if [[ ! -f "$VENV_DIR/bin/cairo-compile" ]]; then
    "$PYTHON" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install "cairo-lang==$CAIRO_LANG"
fi

# Locate the cairo-lang package path and create the custom cairo_path.
# This is required, to let the compiler search for source files first in cairo-lang, then locally if
# not found.
PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_SITE="$VENV_DIR/lib/python$PYTHON_VERSION/site-packages"
CAIRO_PATH="$PYTHON_SITE/:src/"

# Remove external OS implementation to ensure local OS files are used instead of those in
# cairo-lang.
rm -rf "$PYTHON_SITE/starkware/starknet/core/"
rm -f "$PYTHON_SITE/starkware/starknet/common/new_syscalls.cairo"

echo "[INFO] Running cairo-compile: $VENV_DIR/bin/cairo-compile $@ --cairo_path $CAIRO_PATH" >&2
"$VENV_DIR/bin/cairo-compile" "$@" --cairo_path "$CAIRO_PATH"
