// Primitive roots of unity of orders 2, 4, 8 and 16.
// Use 1 / 3^((PRIME - 1) / 16) as the primitive root of order 16 (3 is a generator of the
// multiplicative group of the field).
const OMEGA_16 = 0x5c3ed0c6f6ac6dd647c9ba3e4721c1eb14011ea3d174c52d7981c5b8145aa75;
const OMEGA_8 = OMEGA_16 * OMEGA_16;
const OMEGA_4 = OMEGA_8 * OMEGA_8;
const OMEGA_2 = OMEGA_4 * OMEGA_4;

// Folds 2 elements into one using one layer of FRI.
func fri_formula2(f_x, f_minus_x, eval_point, x_inv) -> (res: felt) {
    return (res=f_x + f_minus_x + eval_point * x_inv * (f_x - f_minus_x));
}

// Folds 4 elements into one using 2 layers of FRI.
func fri_formula4(values: felt*, eval_point, x_inv) -> (res: felt) {
    // First layer.
    let (g0) = fri_formula2(f_x=values[0], f_minus_x=values[1], eval_point=eval_point, x_inv=x_inv);
    let (g1) = fri_formula2(
        f_x=values[2], f_minus_x=values[3], eval_point=eval_point, x_inv=x_inv * OMEGA_4
    );

    // Second layer.
    return fri_formula2(
        f_x=g0, f_minus_x=g1, eval_point=eval_point * eval_point, x_inv=x_inv * x_inv
    );
}

// Folds 8 elements into one using 3 layers of FRI.
func fri_formula8(values: felt*, eval_point, x_inv) -> (res: felt) {
    // First two layers.
    let (g0) = fri_formula4(values=values, eval_point=eval_point, x_inv=x_inv);
    let (g1) = fri_formula4(values=&values[4], eval_point=eval_point, x_inv=x_inv * OMEGA_8);

    // Last layer.
    tempvar eval_point2 = eval_point * eval_point;
    let eval_point4 = eval_point2 * eval_point2;

    tempvar x_inv2 = x_inv * x_inv;
    let x_inv4 = x_inv2 * x_inv2;
    return fri_formula2(f_x=g0, f_minus_x=g1, eval_point=eval_point4, x_inv=x_inv4);
}

// Folds 16 elements into one using 4 layers of FRI.
func fri_formula16(values: felt*, eval_point, x_inv) -> (res: felt) {
    // First three layers.
    let (g0) = fri_formula8(values=values, eval_point=eval_point, x_inv=x_inv);
    let (g1) = fri_formula8(values=&values[8], eval_point=eval_point, x_inv=x_inv * OMEGA_16);

    // Last layer.
    tempvar eval_point2 = eval_point * eval_point;
    tempvar eval_point4 = eval_point2 * eval_point2;
    let eval_point8 = eval_point4 * eval_point4;

    tempvar x_inv2 = x_inv * x_inv;
    tempvar x_inv4 = x_inv2 * x_inv2;
    let x_inv8 = x_inv4 * x_inv4;

    return fri_formula2(f_x=g0, f_minus_x=g1, eval_point=eval_point8, x_inv=x_inv8);
}

// Folds 'coset_size' elements into one using log2(coset_size) layers of FRI.
// 'coset_size' can be 2, 4, 8, or 16.
func fri_formula(values: felt*, eval_point, x_inv, coset_size) -> (res: felt) {
    // Sort by usage frequency.
    if (coset_size == 8) {
        return fri_formula8(values, eval_point, x_inv);
    }
    if (coset_size == 4) {
        return fri_formula4(values, eval_point, x_inv);
    }
    if (coset_size == 16) {
        return fri_formula16(values, eval_point, x_inv);
    }
    if (coset_size == 2) {
        return fri_formula2(values[0], values[1], eval_point, x_inv);
    }

    // Fail.
    assert 1 = 0;
    return (res=0);
}
