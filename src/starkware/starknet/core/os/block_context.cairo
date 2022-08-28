from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.core.os.builtins import BuiltinParams, get_builtin_params
from starkware.starknet.core.os.contracts import ContractClassFact, load_contract_class_facts
from starkware.starknet.core.os.os_config.os_config import StarknetOsConfig

struct BlockInfo {
    // Currently, the block timestamp is not validated.
    block_timestamp: felt,
    block_number: felt,
}

// Represents information that is the same throughout the block.
struct BlockContext {
    // Parameters for select_builtins.
    builtin_params: BuiltinParams*,

    // A list of (class_hash, contract_class) with the contracts that are executed
    // in this block.
    n_contract_class_facts: felt,
    contract_class_facts: ContractClassFact*,
    // The address of the sequencer that is creating this block.
    sequencer_address: felt,
    // Information about the block.
    block_info: BlockInfo,
    // StarknetOsConfig instance.
    starknet_os_config: StarknetOsConfig,
}

// Returns a BlockContext instance.
//
// 'syscall_handler' and 'os_input' should be passed as hint variables.
func get_block_context{pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    block_context: BlockContext*
) {
    alloc_locals;
    let (n_contract_class_facts, contract_class_facts) = load_contract_class_facts();
    let (builtin_params) = get_builtin_params();
    local block_context: BlockContext = BlockContext(
        builtin_params=builtin_params,
        n_contract_class_facts=n_contract_class_facts,
        contract_class_facts=contract_class_facts,
        sequencer_address=nondet %{ os_input.general_config.sequencer_address %},
        block_info=BlockInfo(
            block_timestamp=nondet %{ syscall_handler.block_info.block_timestamp %},
            block_number=nondet %{ syscall_handler.block_info.block_number %}),
        starknet_os_config=StarknetOsConfig(
            chain_id=nondet %{ os_input.general_config.chain_id.value %},
            fee_token_address=nondet %{ os_input.general_config.fee_token_address %}
            ));

    let (__fp__, _) = get_fp_and_pc();
    return (block_context=&block_context);
}
