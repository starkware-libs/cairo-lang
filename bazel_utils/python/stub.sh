#!/bin/bash

# This script runs either python or pypy depending on the name of the module that is being run.
# This script is needed because Bazel only supports one python interpreter.

# --- begin runfiles.bash initialization v2 ---
# Copy-pasted from the Bazel Bash runfiles library v2.
set -uo pipefail; f=bazel_tools/tools/bash/runfiles/runfiles.bash
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null || \
  source "$0.runfiles/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  { echo>&2 "ERROR: cannot find $f"; exit 1; }; f=; set -e
# --- end runfiles.bash initialization v2 ---

set +e

python_interpreter="$(rlocation "python3_x86_64-unknown-linux-gnu/bin/python3")"
if [[ -x "$(rlocation "pypy3.9/bin/pypy3.9")" ]]; then
  if [[ $1 == *_uses_pypy_.py ]]; then
    python_interpreter="$(rlocation "pypy3.9/bin/pypy3.9")"
  fi
fi

if [[ ! -x "$python_interpreter" ]]; then
  echo "Could not find interpreter $python_interpreter" >&2
  exit 1
fi

exec "$python_interpreter" "$@"
