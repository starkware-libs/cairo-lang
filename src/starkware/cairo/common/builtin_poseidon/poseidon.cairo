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
    let elements_end = &elements[n];
    // Apply the sponge construction to digest many elements.
    // To distinguish between the use cases the capacity element is initialized to 0.
    // To distinguish between different input sizes always pad with 1 and possibly with another 0 to
    // complete to an even sized input.
    tempvar state = PoseidonBuiltinState(s0=0, s1=0, s2=0);
    tempvar elements = elements;
    tempvar poseidon_ptr = poseidon_ptr;

    loop:
    if (nondet %{ ids.elements_end - ids.elements >= 10 %} != 0) {
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

        tempvar state = state;
        tempvar elements = &elements[10];
        tempvar poseidon_ptr = poseidon_ptr;
        jmp loop;
    }

    if (nondet %{ ids.elements_end - ids.elements >= 2 %} != 0) {
        assert poseidon_ptr.input = PoseidonBuiltinState(
            s0=state.s0 + elements[0], s1=state.s1 + elements[1], s2=state.s2
        );
        let state = poseidon_ptr.output;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;

        tempvar state = state;
        tempvar elements = &elements[2];
        tempvar poseidon_ptr = poseidon_ptr;
        jmp loop;
    }

    tempvar n = elements_end - elements;

    if (n == 0) {
        // Pad input with [1, 0].
        assert poseidon_ptr.input = PoseidonBuiltinState(s0=state.s0 + 1, s1=state.s1, s2=state.s2);
        let res = poseidon_ptr.output.s0;
        let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;
        return (res=res);
    }

    assert n = 1;
    // Pad input with [1].
    assert poseidon_ptr.input = PoseidonBuiltinState(
        s0=state.s0 + elements[0], s1=state.s1 + 1, s2=state.s2
    );
    let res = poseidon_ptr.output.s0;
    let poseidon_ptr = poseidon_ptr + PoseidonBuiltin.SIZE;
    return (res=res);
}
