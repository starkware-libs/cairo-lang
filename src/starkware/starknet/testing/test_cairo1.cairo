#[starknet::contract]
mod TestContract {
    use starknet::storage_read_syscall;
    use starknet::storage_write_syscall;
    use starknet::storage_access::storage_base_address_from_felt252;
    use starknet::storage_access::storage_address_from_base_and_offset;

    #[storage]
    struct Storage {
    }

    #[external]
    fn read(ref self: ContractState, key: felt252) -> felt252 {
        let domain_address = 0_u32; // Only address_domain 0 is currently supported.
        let storage_address = storage_address_from_base_and_offset(
            storage_base_address_from_felt252(key), 0_u8
        );
        storage_read_syscall(domain_address, storage_address).unwrap_syscall()
    }

    #[external]
    fn write(ref self: ContractState, key: felt252, value: felt252) {
        let domain_address = 0_u32; // Only address_domain 0 is currently supported.
        let storage_address = storage_address_from_base_and_offset(
            storage_base_address_from_felt252(key), 0_u8
        );
        storage_write_syscall(domain_address, storage_address, value).unwrap_syscall();
    }
}
