import json
import os

import cachetools

from starkware.cairo.lang.compiler.program import Program
from starkware.python.utils import get_build_dir_path

PROGRAM_PATH = os.path.join(os.path.dirname(__file__), "program_hash.json")
AGGREGATOR_COMPILED_PATH = get_build_dir_path(
    "src/starkware/starknet/core/aggregator/aggregator.json"
)


@cachetools.cached(cache={})
def get_aggregator_program_hash_with_prefix() -> int:
    return int(json.load(open(PROGRAM_PATH, "rb"))["program_hash_with_aggregator_prefix"], 16)


@cachetools.cached(cache={})
def get_aggregator_program() -> Program:
    return Program.loads(data=open(AGGREGATOR_COMPILED_PATH).read())
