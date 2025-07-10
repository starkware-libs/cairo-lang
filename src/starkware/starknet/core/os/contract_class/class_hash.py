from starkware.starknet.core.os.contract_class.class_hash_utils import py_compute_class_hash
from starkware.starknet.core.os.contract_class.utils import ClassHashType, class_hash_cache_ctx_var
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import ContractClass


def compute_class_hash(contract_class: ContractClass) -> int:
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return py_compute_class_hash(contract_class)

    contract_class_bytes = contract_class.dumps(sort_keys=True).encode()
    key = (ClassHashType.CONTRACT_CLASS, starknet_keccak(data=contract_class_bytes))

    if key not in cache:
        cache[key] = py_compute_class_hash(contract_class)

    return cache[key]
