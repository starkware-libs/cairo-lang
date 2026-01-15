from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    EcOpBuiltin,
    KeccakBuiltin,
    ModBuiltin,
    SignatureBuiltin,
)
from starkware.cairo.common.cairo_ec_op.ec_op import simulate_builtin_ec_op_with_cairo
from starkware.cairo.common.cairo_ecdsa.ecdsa import verify_ecdsa_signature_cairo
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
    let (r) = simulate_builtin_ec_op_with_cairo(p=start[0].p, m=start[0].m, q=start[0].q);
    assert start[0].r = r;
    return verify_ec_op_builtin(start=&start[1], end=end);
}

// Handles the case where the ec_op pointer is uninitialized. That is, not included in the layout.
// If the pointer is uninitialized, it is initialized to a new pointer, and an auto-deduction rule
// is added to the segment to mimic the behavior of the ec_op builtin.
// If the pointer is initialized, it is left unchanged.
func create_ec_op_builtin_segment_if_needed(ec_op_ptr: EcOpBuiltin*) -> (ec_op_ptr: EcOpBuiltin*) {
    if (ec_op_ptr != 0) {
        return (ec_op_ptr=ec_op_ptr);
    }
    alloc_locals;
    local new_ec_op_ptr: EcOpBuiltin*;
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

// Verifies the ec_op builtin if it was simulated and not included in the layout.
// If the pointer was initialized by the layout, the function does nothing.
func verify_ec_op_builtin_if_needed(
    ec_op_ptr: EcOpBuiltin*, ec_op_ptr_orig: EcOpBuiltin*, ec_op_start_ptr: EcOpBuiltin*
) -> (ec_op_ptr: EcOpBuiltin*) {
    if (ec_op_ptr_orig != 0) {
        return (ec_op_ptr=ec_op_ptr);
    }
    verify_ec_op_builtin(start=ec_op_start_ptr, end=ec_op_ptr);
    return (ec_op_ptr=cast(0, EcOpBuiltin*));
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
    let output_array = &output_array[KECCAK_STATE_SIZE_FELTS];
    keccak_builtin_state_to_felts(
        keccak_builtin_state=builtin_start.output, felt_array=output_array
    );
    let output_array = &output_array[KECCAK_STATE_SIZE_FELTS];
    return convert_keccak_builtin_into_25_rep_array(
        builtin_start=&builtin_start[1], builtin_end=builtin_end, output_array=output_array
    );
}

// Handles the case where the keccak pointer is uninitialized. That is, not included in the layout.
// If the pointer is uninitialized, it is initialized to a new pointer, and an auto-deduction rule
// is added to the segment to mimic the behavior of the keccak builtin.
// If the pointer is initialized, it is left unchanged.
func create_keccak_builtin_segment_if_needed(keccak_ptr: KeccakBuiltin*) -> (
    keccak_ptr: KeccakBuiltin*
) {
    if (keccak_ptr != 0) {
        return (keccak_ptr=keccak_ptr);
    }
    alloc_locals;
    local new_keccak_ptr: KeccakBuiltin*;
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

// Verifies of the keccak builtin if it was simulated and not included in the
// layout. If the pointer was initialized by the layout, the function does nothing.
func verify_keccak_builtin_if_needed{range_check_ptr: felt, bitwise_ptr: BitwiseBuiltin*}(
    keccak_ptr: KeccakBuiltin*, keccak_ptr_orig: KeccakBuiltin*, keccak_start_ptr: KeccakBuiltin*
) -> (keccak_ptr: KeccakBuiltin*) {
    if (keccak_ptr_orig != 0) {
        return (keccak_ptr=keccak_ptr);
    }
    alloc_locals;
    let (local keccak_25_rep_array_start: felt*) = alloc();
    let (keccak_25_rep_array_end) = convert_keccak_builtin_into_25_rep_array(
        builtin_start=keccak_start_ptr,
        builtin_end=keccak_ptr,
        output_array=keccak_25_rep_array_start,
    );
    finalize_keccak(
        keccak_ptr_start=keccak_25_rep_array_start, keccak_ptr_end=keccak_25_rep_array_end
    );
    return (keccak_ptr=cast(0, KeccakBuiltin*));
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
    verify_ecdsa_signature_cairo(
        message=start.message, public_key=start.pub_key, signature_r=r, signature_s=s
    );
    return verify_ecdsa_builtin(start=&start[1], end=end);
}

// Handles the case where the ecdsa pointer is uninitialized. That is, not included in the layout.
// If the pointer is uninitialized, it is initialized to a new pointer, and a validation rule is
// added to the segment to mimic the behavior of the ecdsa builtin.
// If the pointer is initialized, it is left unchanged.
func create_ecdsa_builtin_segment_if_needed(ecdsa_ptr: SignatureBuiltin*) -> (
    ecdsa_ptr: SignatureBuiltin*
) {
    if (ecdsa_ptr != 0) {
        return (ecdsa_ptr=ecdsa_ptr);
    }
    alloc_locals;
    local new_ecdsa_ptr: SignatureBuiltin*;
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

// Verifies of the ecdsa builtin if it was simulated and not included in the
// layout. If the pointer was initialized by the layout, the function does nothing.
func verify_ecdsa_builtin_if_needed{mul_mod_ptr: ModBuiltin*, range_check96_ptr: felt}(
    ecdsa_ptr: SignatureBuiltin*,
    ecdsa_ptr_orig: SignatureBuiltin*,
    ecdsa_start_ptr: SignatureBuiltin*,
) -> (ecdsa_ptr: SignatureBuiltin*) {
    if (ecdsa_ptr_orig != 0) {
        return (ecdsa_ptr=ecdsa_ptr);
    }
    verify_ecdsa_builtin(start=ecdsa_start_ptr, end=ecdsa_ptr);
    return (ecdsa_ptr=cast(0, SignatureBuiltin*));
}
