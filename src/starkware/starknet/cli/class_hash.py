import argparse

from starkware.cairo.lang.version import __version__
from starkware.cairo.lang.vm.crypto import get_crypto_lib_context_manager
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.services.api.contract_class import ContractClass


def main():
    parser = argparse.ArgumentParser(
        description="A tool to compute the class hash of a StarkNet contract"
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "compiled_contract",
        type=argparse.FileType("r"),
        help="The name of the contract JSON file.",
    )
    parser.add_argument(
        "--flavor",
        type=str,
        default="Release",
        choices=["Debug", "Release", "RelWithDebInfo"],
        help="Build flavor",
    )
    args = parser.parse_args()

    with get_crypto_lib_context_manager(args.flavor):
        compiled_contract = ContractClass.loads(data=args.compiled_contract.read())
        print(hex(compute_class_hash(compiled_contract)))


if __name__ == "__main__":
    main()
