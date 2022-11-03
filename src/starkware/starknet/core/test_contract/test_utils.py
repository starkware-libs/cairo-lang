import functools
import os

from starkware.starknet.services.api.contract_class import ContractClass


@functools.lru_cache(maxsize=None)
def get_contract_class(contract_name: str) -> ContractClass:
    main_dir_path = os.path.dirname(__file__)
    file_path = os.path.join(main_dir_path, contract_name + ".json")

    with open(file_path, "r") as fp:
        return ContractClass.loads(data=fp.read())


def get_test_contract_class() -> ContractClass:
    return get_contract_class("test_contract")
