from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.dict_access import DictAccess

// Maximum length of an edge.
const MAX_LENGTH = 251;

// A struct of globals that are passed throughout the algorithm.
struct ParticiaGlobals {
    // An array of size MAX_LENGTH, where pow2[i] = 2**i.
    pow2: felt*,
    // Offset of the relevant value field in DictAccess.
    // 1 if the previous tree is traversed and 2 if the new tree is traversed.
    access_offset: felt,
}

// Represents an edge node: a subtree with a path, s.t. all leaves not under that path are 0.
struct NodeEdge {
    length: felt,
    path: felt,
    bottom: felt,
}

// Represents a single entry in the siblings list produced by tree traversal.
// The two fields represent:
//   - type == 0: a plain sibling with the given hash/leaf value (0 means empty subtree).
//   - type == 1: a descent of `value` steps (2 <= value <= MAX_LENGTH), compressing `value`
//     consecutive zero siblings on the descent path into a single entry.
struct Sibling {
    type: felt,
    value: felt,
}

// Holds the constants needed for Patricia updates.
struct PatriciaUpdateConstants {
    globals_pow2: felt*,
}

// Splits the given list of dict accesses into two separate lists: one containing all read accesses
// and the other containing all write accesses.
//
// Assumption: The keys in the update_ptr list are unique and sorted.
func split_reads_writes(n_updates: felt, update_ptr: DictAccess*) -> (
    n_reads: felt, reads: DictAccess*, n_writes: felt, writes: DictAccess*
) {
    alloc_locals;
    let (local reads_start: DictAccess*) = alloc();
    let (local writes_start: DictAccess*) = alloc();

    let reads = reads_start;
    let writes = writes_start;
    with reads, writes {
        split_reads_writes_inner(n_updates=n_updates, update_ptr=update_ptr);
    }

    return (
        n_reads=(reads - reads_start) / DictAccess.SIZE,
        reads=reads_start,
        n_writes=(writes - writes_start) / DictAccess.SIZE,
        writes=writes_start,
    );
}

// Helper function for split_reads_writes.
func split_reads_writes_inner{reads: DictAccess*, writes: DictAccess*}(
    n_updates: felt, update_ptr: DictAccess*
) -> () {
    if (n_updates == 0) {
        return ();
    }
    tempvar current_update = update_ptr[0];
    if (current_update.prev_value == current_update.new_value) {
        // Read.
        assert reads[0] = current_update;
        let reads = &reads[1];
        return split_reads_writes_inner(n_updates=n_updates - 1, update_ptr=&update_ptr[1]);
    }

    // Write.
    assert writes[0] = current_update;
    let writes = &writes[1];
    return split_reads_writes_inner(n_updates=n_updates - 1, update_ptr=&update_ptr[1]);
}
