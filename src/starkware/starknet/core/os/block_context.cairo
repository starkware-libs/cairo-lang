from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.core.os.builtins import BuiltinParams, get_builtin_params
from starkware.starknet.core.os.contract_class.compiled_class import (
    CompiledClassFact,
    load_compiled_class_facts,
)
from starkware.starknet.core.os.contract_class.deprecated_compiled_class import (
    DeprecatedCompiledClassFact,
    deprecated_load_compiled_class_facts,
)
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

    // A list of (compiled_class_hash, compiled_class) with the classes that are executed
    // in this block.
    n_compiled_class_facts: felt,
    compiled_class_facts: CompiledClassFact*,

    // A list of (deprecated_compiled_class_hash, deprecated_compiled_class) with
    // the classes that are executed in this block.
    n_deprecated_compiled_class_facts: felt,
    deprecated_compiled_class_facts: DeprecatedCompiledClassFact*,

    // The address of the sequencer that is creating this block.
    sequencer_address: felt,
    // Information about the block.
    block_info: BlockInfo,
    // StarknetOsConfig instance.
    starknet_os_config: StarknetOsConfig,
    // A function pointer to the 'execute_syscalls' function.
    execute_syscalls_ptr: felt*,
    // A function pointer to the 'execute_deprecated_syscalls' function.
    execute_deprecated_syscalls_ptr: felt*,
}

// Returns a BlockContext instance.
//
// 'syscall_handler' and 'os_input' should be passed as hint variables.
func get_block_context{poseidon_ptr: PoseidonBuiltin*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    execute_syscalls_ptr: felt*, execute_deprecated_syscalls_ptr: felt*
) -> (block_context: BlockContext*) {
    alloc_locals;
    let (n_compiled_class_facts, compiled_class_facts) = load_compiled_class_facts();
    let (
        n_deprecated_compiled_class_facts, deprecated_compiled_class_facts
    ) = deprecated_load_compiled_class_facts();
    let (builtin_params) = get_builtin_params();
    local block_context: BlockContext = BlockContext(
        builtin_params=builtin_params,
        n_compiled_class_facts=n_compiled_class_facts,
        compiled_class_facts=compiled_class_facts,
        n_deprecated_compiled_class_facts=n_deprecated_compiled_class_facts,
        deprecated_compiled_class_facts=deprecated_compiled_class_facts,
        sequencer_address=nondet %{ os_input.general_config.sequencer_address %},
        block_info=BlockInfo(
            block_timestamp=nondet %{ deprecated_syscall_handler.block_info.block_timestamp %},
            block_number=nondet %{ deprecated_syscall_handler.block_info.block_number %},
        ),
        starknet_os_config=StarknetOsConfig(
            chain_id=nondet %{ os_input.general_config.chain_id.value %},
            fee_token_address=nondet %{ os_input.general_config.fee_token_address %},
        ),
        execute_syscalls_ptr=execute_syscalls_ptr,
        execute_deprecated_syscalls_ptr=execute_deprecated_syscalls_ptr,
    );

    let (__fp__, _) = get_fp_and_pc();
    return (block_context=&block_context);
}
