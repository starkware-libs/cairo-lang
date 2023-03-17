#[contract]
mod TestContract {
    use starknet::storage_read_syscall;
    use starknet::storage_write_syscall;
    use starknet::syscalls::emit_event_syscall;
    use starknet::StorageAddress;
    use starknet::ContractAddress;
    use starknet::storage_access::storage_base_address_from_felt252;
    use starknet::storage_access::storage_address_from_base_and_offset;
    use starknet::class_hash::ClassHash;
    use starknet::class_hash::ClassHashSerde;
    use starknet::ContractAddressIntoFelt252;
    use traits::Into;
    use array::SpanTrait;
    use array::ArrayTrait;
    use box::BoxTrait;

    const UNEXPECTED_ERROR: felt252 = 'UNEXPECTED ERROR';

    struct Storage {
        my_storage_var: felt252
    }

    #[external]
    fn test(ref arg: felt252, arg1: felt252, arg2: felt252) -> felt252 {
        let x = my_storage_var::read();
        my_storage_var::write(x + 1);
        x + 1
    }

    #[external]
    fn test_storage_read(address: felt252) -> felt252 {
        let domain_address = 0_u32; // Only address_domain 0 is currently supported.
        let storage_address = storage_address_from_base_and_offset(
            storage_base_address_from_felt252(address), 0_u8
        );
        storage_read_syscall(domain_address, storage_address).unwrap_syscall()
    }

    #[external]
    fn test_storage_write(address: felt252, value: felt252) {
        let domain_address = 0_u32; // Only address_domain 0 is currently supported.
        let storage_address = storage_address_from_base_and_offset(
            storage_base_address_from_felt252(address), 0_u8
        );
        storage_write_syscall(domain_address, storage_address, value).unwrap_syscall();
    }

    #[external]
    fn test_get_execution_info(
        // Expected block info.
        block_number: felt252,
        block_timestamp: felt252,
        sequencer_address: felt252,
        // Expected transaction info.
        version: felt252,
        account_address: felt252,
        max_fee: felt252,
        chain_id: felt252,
        nonce: felt252,
        // Expected call info.
        caller_address: felt252,
        contract_address: felt252,
        entry_point_selector: felt252,
    ) {
        let execution_info = starknet::get_execution_info().unbox();
        let block_info = execution_info.block_info.unbox();
        assert(block_info.block_number.into() == block_number, UNEXPECTED_ERROR);
        assert(block_info.block_timestamp.into() == block_timestamp, UNEXPECTED_ERROR);
        assert(block_info.sequencer_address.into() == sequencer_address, UNEXPECTED_ERROR);

        let tx_info = execution_info.tx_info.unbox();
        assert(tx_info.version == version, UNEXPECTED_ERROR);
        assert(tx_info.account_contract_address.into() == account_address, UNEXPECTED_ERROR);
        assert(tx_info.max_fee.into() == max_fee, UNEXPECTED_ERROR);
        assert(tx_info.signature.len() == 1_u32, UNEXPECTED_ERROR);
        let transaction_hash = *tx_info.signature.at(0_u32);
        assert(tx_info.transaction_hash == transaction_hash, UNEXPECTED_ERROR);
        assert(tx_info.chain_id == chain_id, UNEXPECTED_ERROR);
        assert(tx_info.nonce == nonce, UNEXPECTED_ERROR);

        assert(execution_info.caller_address.into() == caller_address, UNEXPECTED_ERROR);
        assert(execution_info.contract_address.into() == contract_address, UNEXPECTED_ERROR);
        assert(
            execution_info.entry_point_selector == entry_point_selector, UNEXPECTED_ERROR
        );
    }

    #[external]
    fn test_emit_event(keys: Array::<felt252>, data: Array::<felt252>) {
        emit_event_syscall(keys.span(), data.span()).unwrap_syscall();
    }

    #[external]
    fn test_call_contract(
        contract_address: ContractAddress, entry_point_selector: felt252, calldata: Array::<felt252>
    ) {
        starknet::call_contract_syscall(
            contract_address, entry_point_selector, calldata.span()
        ).unwrap_syscall();
    }

    #[external]
    fn test_library_call(
        class_hash: ClassHash, entry_point_selector: felt252, calldata: Array::<felt252>
    ) {
        starknet::syscalls::library_call_syscall(
            class_hash, entry_point_selector, calldata.span()
        ).unwrap_syscall();
    }

    #[external]
    fn assert_eq(x: felt252, y: felt252) -> felt252{
        assert(x == y, 'x != y');
        'success'
    }

}

