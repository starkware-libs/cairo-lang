#!/usr/bin/env python3

import json
import os
import subprocess
from argparse import ArgumentParser

BAD_BRANCH_IDENTIFIER = "BADB51"


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--input_json",
        type=str,
        help="The path to the combined.json file.",
        required=True,
    )
    parser.add_argument(
        "--artifacts_dir",
        type=str,
        help="The directory of the resulted compiled contracts.",
        required=True,
    )
    parser.add_argument("--source_dir", type=str, required=True)
    parser.add_argument("--contracts", type=str, nargs="*", help="Contracts list.", required=True)
    args = parser.parse_args()

    with open(os.path.join(args.input_json)) as fp:
        combined_json = json.load(fp)

    git_commit = BAD_BRANCH_IDENTIFIER
    try:
        git_commit = (
            subprocess.check_output("git rev-parse HEAD".split(), stderr=subprocess.DEVNULL)
            .decode("ascii")
            .strip()[:6]
        )
    except Exception:
        pass

    for path_and_name, val in combined_json["contracts"].items():
        path, contract_name = path_and_name.split(":")
        compiled_path = os.path.relpath(
            os.path.join(os.path.dirname(path), f"{contract_name}.json"), start=args.source_dir
        )
        if compiled_path not in args.contracts:
            continue

        # 1. We cannot put "0x" in case of empty bin, as this would not prevent
        #    loading an empty (virtual) contract. (We want it to fail)
        # 2. Note that we can't put an assert len(val['bin']) > 0 here, because some contracts
        #    are pure virtual and others lack external and public functions.
        bytecode = None
        if len(val["bin"]) > 0:
            bytecode = "0x" + val["bin"]

        # Support both solc-0.6 & solc-0.8 output format.
        # In solc-0.6 the abi is a list in a json string,
        # whereas in 0.8 it's a plain json.
        try:
            abi = json.loads(val["abi"])
        except TypeError:
            abi = val["abi"]

        artifact = {
            "contractName": contract_name,
            "abi": abi,
            "bytecode": bytecode,
            "build_tag": git_commit,
        }

        destination_filename = os.path.join(args.artifacts_dir, compiled_path)
        with open(destination_filename, "w") as fp:
            json.dump(artifact, fp, indent=4)


if __name__ == "__main__":
    main()
