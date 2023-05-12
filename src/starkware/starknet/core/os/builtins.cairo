from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    EcOpBuiltin,
    HashBuiltin,
    PoseidonBuiltin,
    SignatureBuiltin,
)
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.builtins.segment_arena.segment_arena import SegmentArenaBuiltin

struct BuiltinPointers {
    pedersen: HashBuiltin*,
    range_check: felt,
    ecdsa: felt,
    bitwise: felt,
    ec_op: felt,
    poseidon: PoseidonBuiltin*,
    segment_arena: SegmentArenaBuiltin*,
}

// A struct containing the ASCII encoding of each builtin.
struct BuiltinEncodings {
    pedersen: felt,
    range_check: felt,
    ecdsa: felt,
    bitwise: felt,
    ec_op: felt,
    poseidon: felt,
    segment_arena: felt,
}

// A struct containing the instance size of each builtin.
struct BuiltinInstanceSizes {
    pedersen: felt,
    range_check: felt,
    ecdsa: felt,
    bitwise: felt,
    ec_op: felt,
    poseidon: felt,
    segment_arena: felt,
}

struct BuiltinParams {
    builtin_encodings: BuiltinEncodings*,
    builtin_instance_sizes: BuiltinInstanceSizes*,
}

func get_builtin_params() -> (builtin_params: BuiltinParams*) {
    alloc_locals;
    let (local __fp__, _) = get_fp_and_pc();

    local builtin_encodings: BuiltinEncodings = BuiltinEncodings(
        pedersen='pedersen',
        range_check='range_check',
        ecdsa='ecdsa',
        bitwise='bitwise',
        ec_op='ec_op',
        poseidon='poseidon',
        segment_arena='segment_arena',
    );

    local builtin_instance_sizes: BuiltinInstanceSizes = BuiltinInstanceSizes(
        pedersen=HashBuiltin.SIZE,
        range_check=1,
        ecdsa=SignatureBuiltin.SIZE,
        bitwise=BitwiseBuiltin.SIZE,
        ec_op=EcOpBuiltin.SIZE,
        poseidon=PoseidonBuiltin.SIZE,
        segment_arena=SegmentArenaBuiltin.SIZE,
    );

    local builtin_params: BuiltinParams = BuiltinParams(
        builtin_encodings=&builtin_encodings, builtin_instance_sizes=&builtin_instance_sizes
    );
    return (builtin_params=&builtin_params);
}
