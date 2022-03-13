import os

from starkware.starknet.services.api.contract_definition import ContractDefinition


def get_contract_definition(contract_name: str) -> ContractDefinition:
    main_dir_path = os.path.dirname(__file__)
    file_path = os.path.join(main_dir_path, contract_name + ".json")

    with open(file_path, "r") as fp:
        return ContractDefinition.loads(fp.read())


def get_test_contract_definition() -> ContractDefinition:
    return get_contract_definition("test_contract")
