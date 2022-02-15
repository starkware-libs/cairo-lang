from starkware.cairo.common.cairo_builtins import BitwiseBuiltin, HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc

struct BuiltinPointers:
    member pedersen : HashBuiltin*
    member range_check : felt
    member ecdsa : felt
    member bitwise : felt
end

# A struct containing the ASCII encoding of each builtin.
struct BuiltinEncodings:
    member pedersen : felt
    member range_check : felt
    member ecdsa : felt
    member bitwise : felt
end

# A struct containing the instance size of each builtin.
struct BuiltinInstanceSizes:
    member pedersen : felt
    member range_check : felt
    member ecdsa : felt
    member bitwise : felt
end

struct BuiltinParams:
    member builtin_encodings : BuiltinEncodings*
    member builtin_instance_sizes : BuiltinInstanceSizes*
end

func get_builtin_params() -> (builtin_params : BuiltinParams*):
    alloc_locals
    let (local __fp__, _) = get_fp_and_pc()

    local builtin_encodings : BuiltinEncodings = BuiltinEncodings(
        pedersen='pedersen',
        range_check='range_check',
        ecdsa='ecdsa',
        bitwise='bitwise')

    local builtin_instance_sizes : BuiltinInstanceSizes = BuiltinInstanceSizes(
        pedersen=HashBuiltin.SIZE,
        range_check=1,
        ecdsa=SignatureBuiltin.SIZE,
        bitwise=BitwiseBuiltin.SIZE)

    local builtin_params : BuiltinParams = BuiltinParams(
        builtin_encodings=&builtin_encodings,
        builtin_instance_sizes=&builtin_instance_sizes)
    return (builtin_params=&builtin_params)
end
