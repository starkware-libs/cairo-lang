from starkware.cairo.common.builtin_poseidon.poseidon import poseidon_hash_many
from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.starknet.common.storage import normalize_address

const CONTRACT_CLASS_VERSION = 'CONTRACT_CLASS_V0.1.0';

struct ContractEntryPoint {
    // A field element that encodes the signature of the called function.
    selector: felt,
    function_idx: felt,
}

struct ContractClass {
    contract_class_version: felt,

    // The length and pointer to the external entry point table of the contract.
    n_external_functions: felt,
    external_functions: ContractEntryPoint*,

    // The length and pointer to the L1 handler entry point table of the contract.
    n_l1_handlers: felt,
    l1_handlers: ContractEntryPoint*,

    // The length and pointer to the constructor entry point table of the contract.
    n_constructors: felt,
    constructors: ContractEntryPoint*,

    // starknet_keccak of the contract ABI.
    // Note that the OS does not enforce any constraints on this value.
    abi_hash: felt,

    // The length and pointer of the Sierra program.
    sierra_program_length: felt,
    sierra_program_ptr: felt*,
}

// Holds the hashes of the contract class components, to be used for calculating the final hash.
// Note: the order of the struct members must not be changed since it determines the hash order.
struct ContractClassComponentHashes {
    contract_class_version: felt,
    external_functions_hash: felt,
    l1_handlers_hash: felt,
    constructors_hash: felt,
    abi_hash: felt,
    sierra_program_hash: felt,
}

func class_hash{poseidon_ptr: PoseidonBuiltin*, range_check_ptr: felt}(
    contract_class: ContractClass*
) -> felt {
    let contract_class_component_hashes = hash_class_components(contract_class=contract_class);
    return finalize_class_hash(contract_class_component_hashes=contract_class_component_hashes);
}

func hash_class_components{poseidon_ptr: PoseidonBuiltin*}(
    contract_class: ContractClass*
) -> ContractClassComponentHashes* {
    alloc_locals;
    assert contract_class.contract_class_version = CONTRACT_CLASS_VERSION;

    // Hash external entry points.
    let (local external_functions_hash) = poseidon_hash_many(
        n=contract_class.n_external_functions * ContractEntryPoint.SIZE,
        elements=contract_class.external_functions,
    );

    // Hash L1 handler entry points.
    let (local l1_handlers_hash) = poseidon_hash_many(
        n=contract_class.n_l1_handlers * ContractEntryPoint.SIZE,
        elements=contract_class.l1_handlers,
    );

    // Hash constructor entry points.
    let (local constructors_hash) = poseidon_hash_many(
        n=contract_class.n_constructors * ContractEntryPoint.SIZE,
        elements=contract_class.constructors,
    );

    // Hash Sierra program.
    let (local sierra_program_hash) = poseidon_hash_many(
        n=contract_class.sierra_program_length, elements=contract_class.sierra_program_ptr
    );

    tempvar contract_class_component_hashes = new ContractClassComponentHashes(
        contract_class_version=contract_class.contract_class_version,
        external_functions_hash=external_functions_hash,
        l1_handlers_hash=l1_handlers_hash,
        constructors_hash=constructors_hash,
        abi_hash=contract_class.abi_hash,
        sierra_program_hash=sierra_program_hash,
    );
    return contract_class_component_hashes;
}

func finalize_class_hash{poseidon_ptr: PoseidonBuiltin*, range_check_ptr: felt}(
    contract_class_component_hashes: ContractClassComponentHashes*
) -> felt {
    assert contract_class_component_hashes.contract_class_version = CONTRACT_CLASS_VERSION;

    let (hash) = poseidon_hash_many(
        n=ContractClassComponentHashes.SIZE, elements=cast(contract_class_component_hashes, felt*)
    );
    let (normalized_hash) = normalize_address(addr=hash);
    return normalized_hash;
}
