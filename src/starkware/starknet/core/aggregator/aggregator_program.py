import json
import os

import cachetools

PROGRAM_PATH = os.path.join(os.path.dirname(__file__), "program_hash.json")


@cachetools.cached(cache={})
def get_aggregator_program_hash_with_prefix() -> int:
    return int(json.load(open(PROGRAM_PATH, "rb"))["program_hash_with_aggregator_prefix"], 16)
