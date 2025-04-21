from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    EcOpBuiltin,
    KeccakBuiltin,
    ModBuiltin,
    SignatureBuiltin,
)
from starkware.cairo.common.cairo_ec_op.ec_op import verify_simulate_builtin_ec_op_with_cairo
from starkware.cairo.common.cairo_ecdsa.ecdsa import check_ecdsa_signature_cairo
from starkware.cairo.common.cairo_keccak.keccak import KECCAK_STATE_SIZE_FELTS, finalize_keccak
from starkware.cairo.common.ec_point import EcPoint
from starkware.cairo.common.simulate_builtin_keccak_with_cairo.simulate_keccak import (
    keccak_builtin_state_to_felts,
)

// Given a range in a memory segment, assumed to contain only EcOpBuiltin instances, verifies that
// all the EcOpBuiltin instances have the correct values in memory.
func verify_ec_op_builtin(start: EcOpBuiltin*, end: EcOpBuiltin*) {
    if (start == end) {
        return ();
    }
    verify_simulate_builtin_ec_op_with_cairo(input=[start]);
    return verify_ec_op_builtin(start=start + EcOpBuiltin.SIZE, end=end);
}

// Handles the case where the ec_op pointer is uninitialized. That is, not included in the layout.
// If the pointer is uninitialized, it is initialized to a new pointer, and an auto-deduction rule
// is added to the segment to mimic the behavior of the ec_op builtin.
// If the pointer is initialized, it is left unchanged.
func handle_uninitialized_ec_op_builtin(ec_op_ptr: felt) -> (ec_op_ptr: felt) {
    if (ec_op_ptr != 0) {
        return (ec_op_ptr=ec_op_ptr);
    }
    alloc_locals;
    local new_ec_op_ptr;
    %{
        from starkware.cairo.lang.builtins.ec.ec_op_builtin_runner import (
            ec_op_auto_deduction_rule_wrapper,
        )
        ids.new_ec_op_ptr = segments.add()
        vm_add_auto_deduction_rule(
            segment_index=ids.new_ec_op_ptr.segment_index,
            rule=ec_op_auto_deduction_rule_wrapper(ec_op_cache={}),
        )
    %}
    return (ec_op_ptr=new_ec_op_ptr);
}

// Handles the verification of the ec_op builtin if it was simulated and not included in the layout.
// If the pointer was initialized by the layout, the function does nothing.
func handle_ec_op_builtin_verification(
    ec_op_ptr: felt, ec_op_ptr_orig: felt, ec_op_start_ptr: felt
) -> (ec_op_ptr: felt) {
    if (ec_op_ptr_orig != 0) {
        return (ec_op_ptr=ec_op_ptr);
    }
    verify_ec_op_builtin(
        start=cast(ec_op_start_ptr, EcOpBuiltin*), end=cast(ec_op_ptr, EcOpBuiltin*)
    );
    return (ec_op_ptr=ec_op_ptr_orig);
}

// Given a range in a memory segment, assumed to contain only KeccakBuiltin instances, converts
// the input-output pairs of each instance into a representation of 25 felts each, and writes them
// to a new memory segment pointed by output_array.
func convert_keccak_builtin_into_25_rep_array{range_check_ptr: felt}(
    builtin_start: KeccakBuiltin*, builtin_end: KeccakBuiltin*, output_array: felt*
) -> (output_array_end: felt*) {
    if (builtin_start == builtin_end) {
        return (output_array_end=output_array);
    }
    keccak_builtin_state_to_felts(
        keccak_builtin_state=builtin_start.input, felt_array=output_array
    );
    let output_array = output_array + KECCAK_STATE_SIZE_FELTS;
    keccak_builtin_state_to_felts(
        keccak_builtin_state=builtin_start.output, felt_array=output_array
    );
    let output_array = output_array + KECCAK_STATE_SIZE_FELTS;
    return convert_keccak_builtin_into_25_rep_array(
        builtin_start=builtin_start + KeccakBuiltin.SIZE,
        builtin_end=builtin_end,
        output_array=output_array,
    );
}

// Handles the case where the keccak pointer is uninitialized. That is, not included in the layout.
// If the pointer is uninitialized, it is initialized to a new pointer, and an auto-deduction rule
// is added to the segment to mimic the behavior of the keccak builtin.
// If the pointer is initialized, it is left unchanged.
func handle_uninitialized_keccak_builtin(keccak_ptr: felt) -> (keccak_ptr: felt) {
    if (keccak_ptr != 0) {
        return (keccak_ptr=keccak_ptr);
    }
    alloc_locals;
    local new_keccak_ptr;
    %{
        from starkware.cairo.common.keccak_utils.keccak_utils import keccak_func
        from starkware.cairo.lang.builtins.keccak.keccak_builtin_runner import (
            keccak_auto_deduction_rule_wrapper,
        )
        ids.new_keccak_ptr = segments.add()
        vm_add_auto_deduction_rule(
            segment_index=ids.new_keccak_ptr.segment_index,
            rule=keccak_auto_deduction_rule_wrapper(keccak_cache={}),
        )
    %}
    return (keccak_ptr=new_keccak_ptr);
}

// Handles the verification of the keccak builtin if it was simulated and not included in the
// layout. If the pointer was initialized by the layout, the function does nothing.
func handle_keccak_builtin_verification{range_check_ptr: felt, bitwise_ptr: felt}(
    keccak_ptr: felt, keccak_ptr_orig: felt, keccak_start_ptr: felt
) -> (keccak_ptr: felt) {
    if (keccak_ptr_orig != 0) {
        return (keccak_ptr=keccak_ptr);
    }
    alloc_locals;
    let (local keccak_25_rep_array_start: felt*) = alloc();
    let (keccak_25_rep_array_end) = convert_keccak_builtin_into_25_rep_array(
        builtin_start=cast(keccak_start_ptr, KeccakBuiltin*),
        builtin_end=cast(keccak_ptr, KeccakBuiltin*),
        output_array=keccak_25_rep_array_start,
    );
    let bitwise_ptr_cast: BitwiseBuiltin* = cast(bitwise_ptr, BitwiseBuiltin*);
    finalize_keccak{bitwise_ptr=bitwise_ptr_cast}(
        keccak_ptr_start=keccak_25_rep_array_start, keccak_ptr_end=keccak_25_rep_array_end
    );
    let bitwise_ptr = cast(bitwise_ptr_cast, felt);
    return (keccak_ptr=keccak_ptr_orig);
}

// Given a range in a memory segment, assumed to contain only ECDSA builtin instances, verifies
// that all the ECDSA instances have the correct values in memory.
func verify_ecdsa_builtin{range_check96_ptr: felt, mul_mod_ptr: ModBuiltin*}(
    start: SignatureBuiltin*, end: SignatureBuiltin*
) {
    if (start == end) {
        return ();
    }
    tempvar r;
    tempvar s;
    %{ (ids.r, ids.s) = vm_ecdsa_additional_data[ids.start.address_] %}
    let (res) = check_ecdsa_signature_cairo(
        message=start.message, public_key=start.pub_key, signature_r=r, signature_s=s
    );
    assert res = 1;
    return verify_ecdsa_builtin(start=start + SignatureBuiltin.SIZE, end=end);
}

// Handles the case where the ecdsa pointer is uninitialized. That is, not included in the layout.
// If the pointer is uninitialized, it is initialized to a new pointer, and a validation rule is
// added to the segment to mimic the behavior of the ecdsa builtin.
// If the pointer is initialized, it is left unchanged.
func handle_uninitialized_ecdsa_builtin(ecdsa_ptr: felt) -> (ecdsa_ptr: felt) {
    if (ecdsa_ptr != 0) {
        return (ecdsa_ptr=ecdsa_ptr);
    }
    alloc_locals;
    local new_ecdsa_ptr;
    %{
        from starkware.cairo.lang.builtins.signature.signature_builtin_runner import (
            signature_rule_wrapper,
        )
        from starkware.cairo.lang.vm.cairo_runner import verify_ecdsa_sig
        ids.new_ecdsa_ptr = segments.add()
        vm_add_validation_rule(
            segment_index=ids.new_ecdsa_ptr.segment_index,
            rule=signature_rule_wrapper(
                verify_signature_func=verify_ecdsa_sig,
                # Store signatures inside the vm's state. vm_ecdsa_additional_data is dropped
                # into the execution scope by the vm.
                signature_cache=vm_ecdsa_additional_data,
                ),
        )
    %}
    return (ecdsa_ptr=new_ecdsa_ptr);
}

// Handles the verification of the ecdsa builtin if it was simulated and not included in the
// layout. If the pointer was initialized by the layout, the function does nothing.
func handle_ecdsa_builtin_verification{mul_mod_ptr: felt, range_check96_ptr: felt}(
    ecdsa_ptr: felt, ecdsa_ptr_orig: felt, ecdsa_start_ptr: felt
) -> (ecdsa_ptr: felt) {
    if (ecdsa_ptr_orig != 0) {
        return (ecdsa_ptr=ecdsa_ptr);
    }
    let mul_mod_ptr_cast: ModBuiltin* = cast(mul_mod_ptr, ModBuiltin*);
    verify_ecdsa_builtin{mul_mod_ptr=mul_mod_ptr_cast}(
        start=cast(ecdsa_start_ptr, SignatureBuiltin*), end=cast(ecdsa_ptr, SignatureBuiltin*)
    );
    let mul_mod_ptr = cast(mul_mod_ptr_cast, felt);
    return (ecdsa_ptr=ecdsa_ptr_orig);
}
