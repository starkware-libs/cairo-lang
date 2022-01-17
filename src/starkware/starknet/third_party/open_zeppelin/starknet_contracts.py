import os.path
from starkware.starknet.services.api.contract_definition import ContractDefinition

DIR = os.path.dirname(__file__)

account_contract = ContractDefinition.loads(open(os.path.join(DIR, "account.json")).read())
