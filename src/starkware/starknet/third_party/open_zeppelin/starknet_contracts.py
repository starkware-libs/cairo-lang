import os.path

from starkware.starknet.services.api.contract_class import ContractClass

DIR = os.path.dirname(__file__)

account_contract = ContractClass.loads(data=open(os.path.join(DIR, "account.json")).read())
