from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.cairo.common.poseidon_state import PoseidonBuiltinState

// Hashes two elements and retrieves a single field element output.
func poseidon_hash{poseidon_ptr: PoseidonBuiltin*}(x: felt, y: felt) -> (res: felt) {
    // To distinguish between the use cases the capacity element is initialized to 2.
    assert poseidon_ptr.input = PoseidonBuiltinState(s0=x, s1=y, s2=2);

    let res = poseidon_ptr.output.s0;
    let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

    return (res=res);
}

// Hashes one element and retrieves a single field element output.
func poseidon_hash_single{poseidon_ptr: PoseidonBuiltin*}(x: felt) -> (res: felt) {
    // Pad the rate with a zero.
    // To distinguish between the use cases the capacity element is initialized to 1.
    assert poseidon_ptr.input = PoseidonBuiltinState(s0=x, s1=0, s2=1);

    let res = poseidon_ptr.output.s0;
    let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

    return (res=res);
}

// Hashes n elements and retrieves a single field element output.
func poseidon_hash_many{poseidon_ptr: PoseidonBuiltin*}(n: felt, elements: felt*) -> (res: felt) {
    // Apply the sponge construction to digest many elements.
    // To distinguish between the use cases the capacity element is initialized to 0.
    // To distinguish between different input sizes always pad with 1 and possibly with another 0 to
    // complete to an even sized input.
    let state = PoseidonBuiltinState(s0=0, s1=0, s2=0);
    _poseidon_hash_many_inner(state, n, elements);
    let res = poseidon_ptr.output.s0;
    let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;
    return (res=res);
}

// An inner function of the sponge construction. Recursively adds the new elements to the previous
// state and applies the permutation until all elements and the padding are digested.
// At the end of this function poseidon_ptr points to an instance of PoseidonBuiltin with the output
// ready to be used. The caller function must advance poseidon_ptr.
func _poseidon_hash_many_inner{poseidon_ptr: PoseidonBuiltin*}(
    state: PoseidonBuiltinState, n: felt, elements: felt*
) {
    if (nondet %{ ids.n >= 10 %} != 0) {
        assert poseidon_ptr.input = PoseidonBuiltinState(
            s0=state.s0 + elements[0], s1=state.s1 + elements[1], s2=state.s2
        );
        let state = poseidon_ptr.output;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

        assert poseidon_ptr.input = PoseidonBuiltinState(
            s0=state.s0 + elements[2], s1=state.s1 + elements[3], s2=state.s2
        );
        let state = poseidon_ptr.output;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

        assert poseidon_ptr.input = PoseidonBuiltinState(
            s0=state.s0 + elements[4], s1=state.s1 + elements[5], s2=state.s2
        );
        let state = poseidon_ptr.output;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

        assert poseidon_ptr.input = PoseidonBuiltinState(
            s0=state.s0 + elements[6], s1=state.s1 + elements[7], s2=state.s2
        );
        let state = poseidon_ptr.output;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

        assert poseidon_ptr.input = PoseidonBuiltinState(
            s0=state.s0 + elements[8], s1=state.s1 + elements[9], s2=state.s2
        );
        let state = poseidon_ptr.output;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

        return _poseidon_hash_many_inner(state, n - 10, &elements[10]);
    }

    if (nondet %{ ids.n >= 2 %} != 0) {
        assert poseidon_ptr.input = PoseidonBuiltinState(
            s0=state.s0 + elements[0], s1=state.s1 + elements[1], s2=state.s2
        );
        let state = poseidon_ptr.output;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;
        return _poseidon_hash_many_inner(state, n - 2, &elements[2]);
    }

    if (n == 0) {
        // Pad input with [1, 0].
        assert poseidon_ptr.input = PoseidonBuiltinState(s0=state.s0 + 1, s1=state.s1, s2=state.s2);
        return ();
    }

    assert n = 1;
    // Pad input with [1].
    assert poseidon_ptr.input = PoseidonBuiltinState(
        s0=state.s0 + elements[0], s1=state.s1 + 1, s2=state.s2
    );
    return ();
}
