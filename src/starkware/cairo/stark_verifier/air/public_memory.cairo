from starkware.cairo.common.uint256 import Uint256

// Information about a continuous page (a consecutive section of the public memory)..
// Each such page must be verified externally to the verifier:
//   hash = Hash(
//     memory[start_address], memory[start_address + 1], ..., memory[start_address + size - 1]).
//   prod = prod_i (z - ((start_address + i) + alpha * (memory[start_address + i])).
// z, alpha are taken from the interaction values, and can be obtained directly from the
// StarkProof object.
//   z     = interaction_elements.memory__multi_column_perm__perm__interaction_elm.
//   alpha = interaction_elements.memory__multi_column_perm__hash_interaction_elm0.
struct ContinuousPageHeader {
    // Start address.
    start_address: felt,
    // Size of the page.
    size: felt,
    // Hash of the page.
    hash: Uint256,
    // Cumulative product of the page.
    prod: felt,
}

struct AddrValue {
    address: felt,
    value: felt,
}

// Returns the product of (z - (addr + alpha * val)) over a single page.
func get_page_product(z: felt, alpha: felt, data_len: felt, data: AddrValue*) -> (res: felt) {
    if (data_len == 0) {
        return (res=1);
    }
    let (res) = get_page_product(z=z, alpha=alpha, data_len=data_len - 1, data=&data[1]);
    let val = z - (data.address + alpha * data.value);
    return (res=res * val);
}

// Returns the product of all continuous pages.
func get_continuous_pages_product(n_pages: felt, page_headers: ContinuousPageHeader*) -> (
    res: felt, total_length: felt
) {
    if (n_pages == 0) {
        return (res=1, total_length=0);
    }
    let (res, total_length) = get_continuous_pages_product(
        n_pages=n_pages - 1, page_headers=&page_headers[1]
    );
    return (res=res * page_headers.prod, total_length=total_length + page_headers.size);
}
