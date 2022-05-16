import os.path

from starkware.starknet.services.api.contract_definition import ContractDefinition

DIR = os.path.dirname(__file__)

with open(os.path.join(DIR, "account.json")) as fp:
    account_contract = ContractDefinition.loads(fp).read()
