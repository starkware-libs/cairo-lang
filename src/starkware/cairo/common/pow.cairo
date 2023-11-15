from starkware.cairo.common.math import assert_le, sign
from starkware.cairo.common.registers import get_ap, get_fp_and_pc

// Returns base ** exp, for 0 <= exp < 2**251.
func pow{range_check_ptr}(base, exp) -> (res: felt) {
    struct LoopLocals {
        bit: felt,
        temp0: felt,

        res: felt,
        base: felt,
        exp: felt,
    }

    if (exp == 0) {
        return (res=1);
    }

    let initial_locs: LoopLocals* = cast(fp - 2, LoopLocals*);
    initial_locs.res = 1, ap++;
    initial_locs.base = base, ap++;
    initial_locs.exp = exp, ap++;

    loop:
    let prev_locs: LoopLocals* = cast(ap - LoopLocals.SIZE, LoopLocals*);
    let locs: LoopLocals* = cast(ap, LoopLocals*);
    locs.base = prev_locs.base * prev_locs.base, ap++;
    %{ ids.locs.bit = (ids.prev_locs.exp % PRIME) & 1 %}
    jmp odd if locs.bit != 0, ap++;

    even:
    locs.exp = prev_locs.exp / 2, ap++;
    locs.res = prev_locs.res, ap++;
    // exp cannot be 0 here.
    static_assert ap + 1 == locs + LoopLocals.SIZE;
    jmp loop, ap++;

    odd:
    locs.temp0 = prev_locs.exp - 1;
    locs.exp = locs.temp0 / 2, ap++;
    locs.res = prev_locs.res * prev_locs.base, ap++;
    static_assert ap + 1 == locs + LoopLocals.SIZE;
    jmp loop if locs.exp != 0, ap++;

    // Cap the number of steps.
    let (__ap__) = get_ap();
    let (__fp__, _) = get_fp_and_pc();
    let n_steps = (__ap__ - cast(initial_locs, felt*)) / LoopLocals.SIZE - 1;
    assert_le(n_steps, 251);
    return (res=locs.res);
}

// Returns base ** exp, for -rc_bound < exp < rc_bound.
// exp < PRIME / 2 is considered positive and exp > PRIME / 2 is considered negative.
func signed_pow{range_check_ptr}(base, exp) -> felt {
    let exp_sign = sign(exp);
    if (exp_sign == -1) {
        %{ assert ids.base != 0, "Cannot raise 0 to a negative power." %}
        let pos_exp = exp * (-1);
        let (pow_res) = pow(base, pos_exp);
        return 1 / pow_res;
    }
    let (res) = pow(base, exp);
    return res;
}
