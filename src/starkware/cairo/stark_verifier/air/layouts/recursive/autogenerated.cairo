from starkware.cairo.stark_verifier.air.layouts.recursive.global_values import GlobalValues
from starkware.cairo.common.math import safe_div, safe_mult
from starkware.cairo.common.pow import pow

const N_DYNAMIC_PARAMS = 0;
const N_CONSTRAINTS = 93;
const MASK_SIZE = 133;
const CPU_COMPONENT_STEP = 1;
const CPU_COMPONENT_HEIGHT = 16;
const PUBLIC_MEMORY_STEP = 16;
const HAS_DILUTED_POOL = 1;
const DILUTED_SPACING = 4;
const DILUTED_N_BITS = 16;
const PEDERSEN_BUILTIN_RATIO = 128;
const PEDERSEN_BUILTIN_ROW_RATIO = 2048;
const PEDERSEN_BUILTIN_REPETITIONS = 1;
const RANGE_CHECK_BUILTIN_RATIO = 8;
const RANGE_CHECK_BUILTIN_ROW_RATIO = 128;
const RANGE_CHECK_N_PARTS = 8;
const BITWISE__RATIO = 8;
const BITWISE__ROW_RATIO = 128;
const BITWISE__TOTAL_N_BITS = 251;
const HAS_OUTPUT_BUILTIN = 1;
const HAS_PEDERSEN_BUILTIN = 1;
const HAS_RANGE_CHECK_BUILTIN = 1;
const HAS_ECDSA_BUILTIN = 0;
const HAS_BITWISE_BUILTIN = 1;
const HAS_EC_OP_BUILTIN = 0;
const HAS_KECCAK_BUILTIN = 0;
const HAS_POSEIDON_BUILTIN = 0;
const HAS_RANGE_CHECK96_BUILTIN = 0;
const HAS_ADD_MOD_BUILTIN = 0;
const HAS_MUL_MOD_BUILTIN = 0;
const LAYOUT_CODE = 0x726563757273697665;
const CONSTRAINT_DEGREE = 2;
const LOG_CPU_COMPONENT_HEIGHT = 4;
const NUM_COLUMNS_FIRST = 7;
const NUM_COLUMNS_SECOND = 3;
const IS_DYNAMIC_AIR = 0;

func eval_composition_polynomial{range_check_ptr}(
    mask_values: felt*,
    constraint_coefficients: felt*,
    point: felt,
    trace_generator: felt,
    global_values: GlobalValues*,
) -> (res: felt) {
    alloc_locals;

    // Compute powers.
    let (local pow0) = pow(point, (safe_div(global_values.trace_length, 2048)));
    local pow1 = pow0 * pow0;  // pow(point, (safe_div(global_values.trace_length, 1024))).
    let (local pow2) = pow(point, (safe_div(global_values.trace_length, 128)));
    let (local pow3) = pow(point, (safe_div(global_values.trace_length, 32)));
    local pow4 = pow3 * pow3;  // pow(point, (safe_div(global_values.trace_length, 16))).
    let (local pow5) = pow(point, (safe_div(global_values.trace_length, 4)));
    local pow6 = pow5 * pow5;  // pow(point, (safe_div(global_values.trace_length, 2))).
    local pow7 = pow6 * pow6;  // pow(point, global_values.trace_length).
    let (local pow8) = pow(trace_generator, global_values.trace_length - 128);
    let (local pow9) = pow(trace_generator, global_values.trace_length - 2048);
    let (local pow10) = pow(trace_generator, global_values.trace_length - 1);
    let (local pow11) = pow(trace_generator, global_values.trace_length - 4);
    let (local pow12) = pow(trace_generator, global_values.trace_length - 2);
    let (local pow13) = pow(trace_generator, global_values.trace_length - 16);
    let (local pow14) = pow(trace_generator, (safe_div(global_values.trace_length, 2)));
    let (local pow15) = pow(
        trace_generator, (safe_div((safe_mult(255, global_values.trace_length)), 256))
    );
    let (local pow16) = pow(trace_generator, (safe_div(global_values.trace_length, 64)));
    local pow17 = pow16 * pow16;  // pow(trace_generator, (safe_div(global_values.trace_length, 32))).
    local pow18 = pow16 * pow17;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 64))).
    local pow19 = pow16 * pow18;  // pow(trace_generator, (safe_div(global_values.trace_length, 16))).
    local pow20 = pow16 * pow19;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 64))).
    local pow21 = pow16 * pow20;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 32))).
    local pow22 = pow16 * pow21;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 64))).
    local pow23 = pow16 * pow22;  // pow(trace_generator, (safe_div(global_values.trace_length, 8))).
    local pow24 = pow16 * pow23;  // pow(trace_generator, (safe_div((safe_mult(9, global_values.trace_length)), 64))).
    local pow25 = pow16 * pow24;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 32))).
    local pow26 = pow16 * pow25;  // pow(trace_generator, (safe_div((safe_mult(11, global_values.trace_length)), 64))).
    local pow27 = pow16 * pow26;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 16))).
    local pow28 = pow16 * pow27;  // pow(trace_generator, (safe_div((safe_mult(13, global_values.trace_length)), 64))).
    local pow29 = pow16 * pow28;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 32))).
    local pow30 = pow16 * pow29;  // pow(trace_generator, (safe_div((safe_mult(15, global_values.trace_length)), 64))).
    let (local pow31) = pow(
        trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 4))
    );
    local pow32 = pow27 * pow31;  // pow(trace_generator, (safe_div((safe_mult(15, global_values.trace_length)), 16))).
    local pow33 = pow18 * pow32;  // pow(trace_generator, (safe_div((safe_mult(63, global_values.trace_length)), 64))).

    // Compute domains.
    tempvar domain0 = pow7 - 1;
    tempvar domain1 = pow6 - 1;
    tempvar domain2 = pow5 - 1;
    tempvar domain3 = pow4 - pow32;
    tempvar domain4 = pow4 - 1;
    tempvar domain5 = pow3 - 1;
    tempvar domain6 = pow2 - 1;
    tempvar domain7 = pow2 - pow31;
    tempvar temp = pow2 - pow16;
    tempvar temp = temp * (pow2 - pow17);
    tempvar temp = temp * (pow2 - pow18);
    tempvar temp = temp * (pow2 - pow19);
    tempvar temp = temp * (pow2 - pow20);
    tempvar temp = temp * (pow2 - pow21);
    tempvar temp = temp * (pow2 - pow22);
    tempvar temp = temp * (pow2 - pow23);
    tempvar temp = temp * (pow2 - pow24);
    tempvar temp = temp * (pow2 - pow25);
    tempvar temp = temp * (pow2 - pow26);
    tempvar temp = temp * (pow2 - pow27);
    tempvar temp = temp * (pow2 - pow28);
    tempvar temp = temp * (pow2 - pow29);
    tempvar temp = temp * (pow2 - pow30);
    tempvar domain8 = temp * (domain6);
    tempvar domain9 = pow1 - 1;
    tempvar domain10 = pow1 - pow15;
    tempvar domain11 = pow1 - pow33;
    tempvar domain12 = pow0 - pow14;
    tempvar domain13 = pow0 - 1;
    tempvar domain14 = point - pow13;
    tempvar domain15 = point - 1;
    tempvar domain16 = point - pow12;
    tempvar domain17 = point - pow11;
    tempvar domain18 = point - pow10;
    tempvar domain19 = point - pow9;
    tempvar domain20 = point - pow8;

    // Fetch mask variables.
    tempvar column0_row0 = mask_values[0];
    tempvar column0_row1 = mask_values[1];
    tempvar column0_row2 = mask_values[2];
    tempvar column0_row3 = mask_values[3];
    tempvar column0_row4 = mask_values[4];
    tempvar column0_row5 = mask_values[5];
    tempvar column0_row6 = mask_values[6];
    tempvar column0_row7 = mask_values[7];
    tempvar column0_row8 = mask_values[8];
    tempvar column0_row9 = mask_values[9];
    tempvar column0_row10 = mask_values[10];
    tempvar column0_row11 = mask_values[11];
    tempvar column0_row12 = mask_values[12];
    tempvar column0_row13 = mask_values[13];
    tempvar column0_row14 = mask_values[14];
    tempvar column0_row15 = mask_values[15];
    tempvar column1_row0 = mask_values[16];
    tempvar column1_row1 = mask_values[17];
    tempvar column1_row2 = mask_values[18];
    tempvar column1_row4 = mask_values[19];
    tempvar column1_row6 = mask_values[20];
    tempvar column1_row8 = mask_values[21];
    tempvar column1_row10 = mask_values[22];
    tempvar column1_row12 = mask_values[23];
    tempvar column1_row14 = mask_values[24];
    tempvar column1_row16 = mask_values[25];
    tempvar column1_row18 = mask_values[26];
    tempvar column1_row20 = mask_values[27];
    tempvar column1_row22 = mask_values[28];
    tempvar column1_row24 = mask_values[29];
    tempvar column1_row26 = mask_values[30];
    tempvar column1_row28 = mask_values[31];
    tempvar column1_row30 = mask_values[32];
    tempvar column1_row32 = mask_values[33];
    tempvar column1_row33 = mask_values[34];
    tempvar column1_row64 = mask_values[35];
    tempvar column1_row65 = mask_values[36];
    tempvar column1_row88 = mask_values[37];
    tempvar column1_row90 = mask_values[38];
    tempvar column1_row92 = mask_values[39];
    tempvar column1_row94 = mask_values[40];
    tempvar column1_row96 = mask_values[41];
    tempvar column1_row97 = mask_values[42];
    tempvar column1_row120 = mask_values[43];
    tempvar column1_row122 = mask_values[44];
    tempvar column1_row124 = mask_values[45];
    tempvar column1_row126 = mask_values[46];
    tempvar column2_row0 = mask_values[47];
    tempvar column2_row1 = mask_values[48];
    tempvar column3_row0 = mask_values[49];
    tempvar column3_row1 = mask_values[50];
    tempvar column3_row2 = mask_values[51];
    tempvar column3_row3 = mask_values[52];
    tempvar column3_row4 = mask_values[53];
    tempvar column3_row5 = mask_values[54];
    tempvar column3_row8 = mask_values[55];
    tempvar column3_row9 = mask_values[56];
    tempvar column3_row10 = mask_values[57];
    tempvar column3_row11 = mask_values[58];
    tempvar column3_row12 = mask_values[59];
    tempvar column3_row13 = mask_values[60];
    tempvar column3_row16 = mask_values[61];
    tempvar column3_row26 = mask_values[62];
    tempvar column3_row27 = mask_values[63];
    tempvar column3_row42 = mask_values[64];
    tempvar column3_row43 = mask_values[65];
    tempvar column3_row58 = mask_values[66];
    tempvar column3_row74 = mask_values[67];
    tempvar column3_row75 = mask_values[68];
    tempvar column3_row91 = mask_values[69];
    tempvar column3_row122 = mask_values[70];
    tempvar column3_row123 = mask_values[71];
    tempvar column3_row154 = mask_values[72];
    tempvar column3_row202 = mask_values[73];
    tempvar column3_row522 = mask_values[74];
    tempvar column3_row523 = mask_values[75];
    tempvar column3_row1034 = mask_values[76];
    tempvar column3_row1035 = mask_values[77];
    tempvar column3_row2058 = mask_values[78];
    tempvar column4_row0 = mask_values[79];
    tempvar column4_row1 = mask_values[80];
    tempvar column4_row2 = mask_values[81];
    tempvar column4_row3 = mask_values[82];
    tempvar column5_row0 = mask_values[83];
    tempvar column5_row1 = mask_values[84];
    tempvar column5_row2 = mask_values[85];
    tempvar column5_row3 = mask_values[86];
    tempvar column5_row4 = mask_values[87];
    tempvar column5_row5 = mask_values[88];
    tempvar column5_row6 = mask_values[89];
    tempvar column5_row7 = mask_values[90];
    tempvar column5_row8 = mask_values[91];
    tempvar column5_row12 = mask_values[92];
    tempvar column5_row28 = mask_values[93];
    tempvar column5_row44 = mask_values[94];
    tempvar column5_row60 = mask_values[95];
    tempvar column5_row76 = mask_values[96];
    tempvar column5_row92 = mask_values[97];
    tempvar column5_row108 = mask_values[98];
    tempvar column5_row124 = mask_values[99];
    tempvar column5_row1021 = mask_values[100];
    tempvar column5_row1023 = mask_values[101];
    tempvar column5_row1025 = mask_values[102];
    tempvar column5_row1027 = mask_values[103];
    tempvar column5_row2045 = mask_values[104];
    tempvar column6_row0 = mask_values[105];
    tempvar column6_row1 = mask_values[106];
    tempvar column6_row2 = mask_values[107];
    tempvar column6_row3 = mask_values[108];
    tempvar column6_row4 = mask_values[109];
    tempvar column6_row5 = mask_values[110];
    tempvar column6_row7 = mask_values[111];
    tempvar column6_row9 = mask_values[112];
    tempvar column6_row11 = mask_values[113];
    tempvar column6_row13 = mask_values[114];
    tempvar column6_row17 = mask_values[115];
    tempvar column6_row25 = mask_values[116];
    tempvar column6_row768 = mask_values[117];
    tempvar column6_row772 = mask_values[118];
    tempvar column6_row784 = mask_values[119];
    tempvar column6_row788 = mask_values[120];
    tempvar column6_row1004 = mask_values[121];
    tempvar column6_row1008 = mask_values[122];
    tempvar column6_row1022 = mask_values[123];
    tempvar column6_row1024 = mask_values[124];
    tempvar column7_inter1_row0 = mask_values[125];
    tempvar column7_inter1_row1 = mask_values[126];
    tempvar column8_inter1_row0 = mask_values[127];
    tempvar column8_inter1_row1 = mask_values[128];
    tempvar column9_inter1_row0 = mask_values[129];
    tempvar column9_inter1_row1 = mask_values[130];
    tempvar column9_inter1_row2 = mask_values[131];
    tempvar column9_inter1_row5 = mask_values[132];

    // Compute intermediate values.
    tempvar cpu__decode__opcode_range_check__bit_0 = column0_row0 - (column0_row1 + column0_row1);
    tempvar cpu__decode__opcode_range_check__bit_2 = column0_row2 - (column0_row3 + column0_row3);
    tempvar cpu__decode__opcode_range_check__bit_4 = column0_row4 - (column0_row5 + column0_row5);
    tempvar cpu__decode__opcode_range_check__bit_3 = column0_row3 - (column0_row4 + column0_row4);
    tempvar cpu__decode__flag_op1_base_op0_0 = 1 - (
        cpu__decode__opcode_range_check__bit_2 +
        cpu__decode__opcode_range_check__bit_4 +
        cpu__decode__opcode_range_check__bit_3
    );
    tempvar cpu__decode__opcode_range_check__bit_5 = column0_row5 - (column0_row6 + column0_row6);
    tempvar cpu__decode__opcode_range_check__bit_6 = column0_row6 - (column0_row7 + column0_row7);
    tempvar cpu__decode__opcode_range_check__bit_9 = column0_row9 - (column0_row10 + column0_row10);
    tempvar cpu__decode__flag_res_op1_0 = 1 - (
        cpu__decode__opcode_range_check__bit_5 +
        cpu__decode__opcode_range_check__bit_6 +
        cpu__decode__opcode_range_check__bit_9
    );
    tempvar cpu__decode__opcode_range_check__bit_7 = column0_row7 - (column0_row8 + column0_row8);
    tempvar cpu__decode__opcode_range_check__bit_8 = column0_row8 - (column0_row9 + column0_row9);
    tempvar cpu__decode__flag_pc_update_regular_0 = 1 - (
        cpu__decode__opcode_range_check__bit_7 +
        cpu__decode__opcode_range_check__bit_8 +
        cpu__decode__opcode_range_check__bit_9
    );
    tempvar cpu__decode__opcode_range_check__bit_12 = column0_row12 - (
        column0_row13 + column0_row13
    );
    tempvar cpu__decode__opcode_range_check__bit_13 = column0_row13 - (
        column0_row14 + column0_row14
    );
    tempvar cpu__decode__fp_update_regular_0 = 1 - (
        cpu__decode__opcode_range_check__bit_12 + cpu__decode__opcode_range_check__bit_13
    );
    tempvar cpu__decode__opcode_range_check__bit_1 = column0_row1 - (column0_row2 + column0_row2);
    tempvar npc_reg_0 = column3_row0 + cpu__decode__opcode_range_check__bit_2 + 1;
    tempvar cpu__decode__opcode_range_check__bit_10 = column0_row10 - (
        column0_row11 + column0_row11
    );
    tempvar cpu__decode__opcode_range_check__bit_11 = column0_row11 - (
        column0_row12 + column0_row12
    );
    tempvar cpu__decode__opcode_range_check__bit_14 = column0_row14 - (
        column0_row15 + column0_row15
    );
    tempvar memory__address_diff_0 = column4_row2 - column4_row0;
    tempvar range_check16__diff_0 = column5_row6 - column5_row2;
    tempvar pedersen__hash0__ec_subset_sum__bit_0 = column6_row0 - (column6_row4 + column6_row4);
    tempvar pedersen__hash0__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash0__ec_subset_sum__bit_0;
    tempvar range_check_builtin__value0_0 = column5_row12;
    tempvar range_check_builtin__value1_0 = range_check_builtin__value0_0 *
        global_values.offset_size + column5_row28;
    tempvar range_check_builtin__value2_0 = range_check_builtin__value1_0 *
        global_values.offset_size + column5_row44;
    tempvar range_check_builtin__value3_0 = range_check_builtin__value2_0 *
        global_values.offset_size + column5_row60;
    tempvar range_check_builtin__value4_0 = range_check_builtin__value3_0 *
        global_values.offset_size + column5_row76;
    tempvar range_check_builtin__value5_0 = range_check_builtin__value4_0 *
        global_values.offset_size + column5_row92;
    tempvar range_check_builtin__value6_0 = range_check_builtin__value5_0 *
        global_values.offset_size + column5_row108;
    tempvar range_check_builtin__value7_0 = range_check_builtin__value6_0 *
        global_values.offset_size + column5_row124;
    tempvar bitwise__sum_var_0_0 = column1_row0 + column1_row2 * 2 + column1_row4 * 4 +
        column1_row6 * 8 + column1_row8 * 18446744073709551616 + column1_row10 *
        36893488147419103232 + column1_row12 * 73786976294838206464 + column1_row14 *
        147573952589676412928;
    tempvar bitwise__sum_var_8_0 = column1_row16 * 340282366920938463463374607431768211456 +
        column1_row18 * 680564733841876926926749214863536422912 + column1_row20 *
        1361129467683753853853498429727072845824 + column1_row22 *
        2722258935367507707706996859454145691648 + column1_row24 *
        6277101735386680763835789423207666416102355444464034512896 + column1_row26 *
        12554203470773361527671578846415332832204710888928069025792 + column1_row28 *
        25108406941546723055343157692830665664409421777856138051584 + column1_row30 *
        50216813883093446110686315385661331328818843555712276103168;

    // Sum constraints.
    tempvar total_sum = 0;

    // Constraint: cpu/decode/opcode_range_check/bit.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_0 * cpu__decode__opcode_range_check__bit_0 -
        cpu__decode__opcode_range_check__bit_0
    ) * domain3 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[0] * value;

    // Constraint: cpu/decode/opcode_range_check/zero.
    tempvar value = (column0_row0) / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[1] * value;

    // Constraint: cpu/decode/opcode_range_check_input.
    tempvar value = (
        column3_row1 -
        (
            (
                (column0_row0 * global_values.offset_size + column5_row4) *
                global_values.offset_size +
                column5_row8
            ) * global_values.offset_size +
            column5_row0
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[2] * value;

    // Constraint: cpu/decode/flag_op1_base_op0_bit.
    tempvar value = (
        cpu__decode__flag_op1_base_op0_0 * cpu__decode__flag_op1_base_op0_0 -
        cpu__decode__flag_op1_base_op0_0
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[3] * value;

    // Constraint: cpu/decode/flag_res_op1_bit.
    tempvar value = (
        cpu__decode__flag_res_op1_0 * cpu__decode__flag_res_op1_0 - cpu__decode__flag_res_op1_0
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[4] * value;

    // Constraint: cpu/decode/flag_pc_update_regular_bit.
    tempvar value = (
        cpu__decode__flag_pc_update_regular_0 * cpu__decode__flag_pc_update_regular_0 -
        cpu__decode__flag_pc_update_regular_0
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[5] * value;

    // Constraint: cpu/decode/fp_update_regular_bit.
    tempvar value = (
        cpu__decode__fp_update_regular_0 * cpu__decode__fp_update_regular_0 -
        cpu__decode__fp_update_regular_0
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[6] * value;

    // Constraint: cpu/operands/mem_dst_addr.
    tempvar value = (
        column3_row8 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_0 * column6_row9 +
            (1 - cpu__decode__opcode_range_check__bit_0) * column6_row1 +
            column5_row0
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    // Constraint: cpu/operands/mem0_addr.
    tempvar value = (
        column3_row4 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_1 * column6_row9 +
            (1 - cpu__decode__opcode_range_check__bit_1) * column6_row1 +
            column5_row8
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    // Constraint: cpu/operands/mem1_addr.
    tempvar value = (
        column3_row12 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_2 * column3_row0 +
            cpu__decode__opcode_range_check__bit_4 * column6_row1 +
            cpu__decode__opcode_range_check__bit_3 * column6_row9 +
            cpu__decode__flag_op1_base_op0_0 * column3_row5 +
            column5_row4
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    // Constraint: cpu/operands/ops_mul.
    tempvar value = (column6_row5 - column3_row5 * column3_row13) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    // Constraint: cpu/operands/res.
    tempvar value = (
        (1 - cpu__decode__opcode_range_check__bit_9) * column6_row13 -
        (
            cpu__decode__opcode_range_check__bit_5 * (column3_row5 + column3_row13) +
            cpu__decode__opcode_range_check__bit_6 * column6_row5 +
            cpu__decode__flag_res_op1_0 * column3_row13
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    // Constraint: cpu/update_registers/update_pc/tmp0.
    tempvar value = (column6_row3 - cpu__decode__opcode_range_check__bit_9 * column3_row9) *
        domain14 / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    // Constraint: cpu/update_registers/update_pc/tmp1.
    tempvar value = (column6_row11 - column6_row3 * column6_row13) * domain14 / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_negative.
    tempvar value = (
        (1 - cpu__decode__opcode_range_check__bit_9) * column3_row16 +
        column6_row3 * (column3_row16 - (column3_row0 + column3_row13)) -
        (
            cpu__decode__flag_pc_update_regular_0 * npc_reg_0 +
            cpu__decode__opcode_range_check__bit_7 * column6_row13 +
            cpu__decode__opcode_range_check__bit_8 * (column3_row0 + column6_row13)
        )
    ) * domain14 / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_positive.
    tempvar value = (
        (column6_row11 - cpu__decode__opcode_range_check__bit_9) * (column3_row16 - npc_reg_0)
    ) * domain14 / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    // Constraint: cpu/update_registers/update_ap/ap_update.
    tempvar value = (
        column6_row17 -
        (
            column6_row1 +
            cpu__decode__opcode_range_check__bit_10 * column6_row13 +
            cpu__decode__opcode_range_check__bit_11 +
            cpu__decode__opcode_range_check__bit_12 * 2
        )
    ) * domain14 / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    // Constraint: cpu/update_registers/update_fp/fp_update.
    tempvar value = (
        column6_row25 -
        (
            cpu__decode__fp_update_regular_0 * column6_row9 +
            cpu__decode__opcode_range_check__bit_13 * column3_row9 +
            cpu__decode__opcode_range_check__bit_12 * (column6_row1 + 2)
        )
    ) * domain14 / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    // Constraint: cpu/opcodes/call/push_fp.
    tempvar value = (cpu__decode__opcode_range_check__bit_12 * (column3_row9 - column6_row9)) /
        domain4;
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    // Constraint: cpu/opcodes/call/push_pc.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (
            column3_row5 - (column3_row0 + cpu__decode__opcode_range_check__bit_2 + 1)
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    // Constraint: cpu/opcodes/call/off0.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (column5_row0 - global_values.half_offset_size)
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    // Constraint: cpu/opcodes/call/off1.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (
            column5_row8 - (global_values.half_offset_size + 1)
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[21] * value;

    // Constraint: cpu/opcodes/call/flags.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (
            cpu__decode__opcode_range_check__bit_12 +
            cpu__decode__opcode_range_check__bit_12 +
            1 +
            1 -
            (cpu__decode__opcode_range_check__bit_0 + cpu__decode__opcode_range_check__bit_1 + 4)
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    // Constraint: cpu/opcodes/ret/off0.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_13 * (
            column5_row0 + 2 - global_values.half_offset_size
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    // Constraint: cpu/opcodes/ret/off2.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_13 * (
            column5_row4 + 1 - global_values.half_offset_size
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[24] * value;

    // Constraint: cpu/opcodes/ret/flags.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_13 * (
            cpu__decode__opcode_range_check__bit_7 +
            cpu__decode__opcode_range_check__bit_0 +
            cpu__decode__opcode_range_check__bit_3 +
            cpu__decode__flag_res_op1_0 -
            4
        )
    ) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    // Constraint: cpu/opcodes/assert_eq/assert_eq.
    tempvar value = (cpu__decode__opcode_range_check__bit_14 * (column3_row9 - column6_row13)) /
        domain4;
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    // Constraint: initial_ap.
    tempvar value = (column6_row1 - global_values.initial_ap) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    // Constraint: initial_fp.
    tempvar value = (column6_row9 - global_values.initial_ap) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    // Constraint: initial_pc.
    tempvar value = (column3_row0 - global_values.initial_pc) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    // Constraint: final_ap.
    tempvar value = (column6_row1 - global_values.final_ap) / domain14;
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    // Constraint: final_fp.
    tempvar value = (column6_row9 - global_values.initial_ap) / domain14;
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    // Constraint: final_pc.
    tempvar value = (column3_row0 - global_values.final_pc) / domain14;
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    // Constraint: memory/multi_column_perm/perm/init0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column4_row0 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column4_row1
            )
        ) * column9_inter1_row0 +
        column3_row0 +
        global_values.memory__multi_column_perm__hash_interaction_elm0 * column3_row1 -
        global_values.memory__multi_column_perm__perm__interaction_elm
    ) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    // Constraint: memory/multi_column_perm/perm/step0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column4_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column4_row3
            )
        ) * column9_inter1_row2 -
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column3_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column3_row3
            )
        ) * column9_inter1_row0
    ) * domain16 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    // Constraint: memory/multi_column_perm/perm/last.
    tempvar value = (
        column9_inter1_row0 - global_values.memory__multi_column_perm__perm__public_memory_prod
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    // Constraint: memory/diff_is_bit.
    tempvar value = (memory__address_diff_0 * memory__address_diff_0 - memory__address_diff_0) *
        domain16 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    // Constraint: memory/is_func.
    tempvar value = ((memory__address_diff_0 - 1) * (column4_row1 - column4_row3)) * domain16 /
        domain1;
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    // Constraint: memory/initial_addr.
    tempvar value = (column4_row0 - 1) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    // Constraint: public_memory_addr_zero.
    tempvar value = (column3_row2) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    // Constraint: public_memory_value_zero.
    tempvar value = (column3_row3) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    // Constraint: range_check16/perm/init0.
    tempvar value = (
        (global_values.range_check16__perm__interaction_elm - column5_row2) * column9_inter1_row1 +
        column5_row0 -
        global_values.range_check16__perm__interaction_elm
    ) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    // Constraint: range_check16/perm/step0.
    tempvar value = (
        (global_values.range_check16__perm__interaction_elm - column5_row6) * column9_inter1_row5 -
        (global_values.range_check16__perm__interaction_elm - column5_row4) * column9_inter1_row1
    ) * domain17 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    // Constraint: range_check16/perm/last.
    tempvar value = (column9_inter1_row1 - global_values.range_check16__perm__public_memory_prod) /
        domain17;
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    // Constraint: range_check16/diff_is_bit.
    tempvar value = (range_check16__diff_0 * range_check16__diff_0 - range_check16__diff_0) *
        domain17 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    // Constraint: range_check16/minimum.
    tempvar value = (column5_row2 - global_values.range_check_min) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    // Constraint: range_check16/maximum.
    tempvar value = (column5_row2 - global_values.range_check_max) / domain17;
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    // Constraint: diluted_check/permutation/init0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column2_row0) *
        column8_inter1_row0 +
        column1_row0 -
        global_values.diluted_check__permutation__interaction_elm
    ) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    // Constraint: diluted_check/permutation/step0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column2_row1) *
        column8_inter1_row1 -
        (global_values.diluted_check__permutation__interaction_elm - column1_row1) *
        column8_inter1_row0
    ) * domain18 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    // Constraint: diluted_check/permutation/last.
    tempvar value = (
        column8_inter1_row0 - global_values.diluted_check__permutation__public_memory_prod
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    // Constraint: diluted_check/init.
    tempvar value = (column7_inter1_row0 - 1) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    // Constraint: diluted_check/first_element.
    tempvar value = (column2_row0 - global_values.diluted_check__first_elm) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    // Constraint: diluted_check/step.
    tempvar value = (
        column7_inter1_row1 -
        (
            column7_inter1_row0 * (
                1 + global_values.diluted_check__interaction_z * (column2_row1 - column2_row0)
            ) +
            global_values.diluted_check__interaction_alpha * (column2_row1 - column2_row0) * (
                column2_row1 - column2_row0
            )
        )
    ) * domain18 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    // Constraint: diluted_check/last.
    tempvar value = (column7_inter1_row0 - global_values.diluted_check__final_cum_val) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column6_row7 * (column6_row0 - (column6_row4 + column6_row4))) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column6_row7 * (
            column6_row4 -
            3138550867693340381917894711603833208051177722232017256448 * column6_row768
        )
    ) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column6_row7 - column6_row1022 * (column6_row768 - (column6_row772 + column6_row772))
    ) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column6_row1022 * (column6_row772 - 8 * column6_row784)) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column6_row1022 -
        (column6_row1004 - (column6_row1008 + column6_row1008)) * (
            column6_row784 - (column6_row788 + column6_row788)
        )
    ) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column6_row1004 - (column6_row1008 + column6_row1008)) * (
            column6_row788 - 18014398509481984 * column6_row1004
        )
    ) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (pedersen__hash0__ec_subset_sum__bit_0 - 1)
    ) * domain10 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_extraction_end.
    tempvar value = (column6_row0) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/zeros_tail.
    tempvar value = (column6_row0) / domain10;
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column5_row3 - global_values.pedersen__points__y) -
        column6_row2 * (column5_row1 - global_values.pedersen__points__x)
    ) * domain10 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/x.
    tempvar value = (
        column6_row2 * column6_row2 -
        pedersen__hash0__ec_subset_sum__bit_0 * (
            column5_row1 + global_values.pedersen__points__x + column5_row5
        )
    ) * domain10 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column5_row3 + column5_row7) -
        column6_row2 * (column5_row1 - column5_row5)
    ) * domain10 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column5_row5 - column5_row1)) *
        domain10 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column5_row7 - column5_row3)) *
        domain10 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    // Constraint: pedersen/hash0/copy_point/x.
    tempvar value = (column5_row1025 - column5_row1021) * domain12 / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    // Constraint: pedersen/hash0/copy_point/y.
    tempvar value = (column5_row1027 - column5_row1023) * domain12 / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    // Constraint: pedersen/hash0/init/x.
    tempvar value = (column5_row1 - global_values.pedersen__shift_point.x) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    // Constraint: pedersen/hash0/init/y.
    tempvar value = (column5_row3 - global_values.pedersen__shift_point.y) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    // Constraint: pedersen/input0_value0.
    tempvar value = (column3_row11 - column6_row0) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    // Constraint: pedersen/input0_addr.
    tempvar value = (column3_row2058 - (column3_row522 + 1)) * domain19 / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    // Constraint: pedersen/init_addr.
    tempvar value = (column3_row10 - global_values.initial_pedersen_addr) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    // Constraint: pedersen/input1_value0.
    tempvar value = (column3_row1035 - column6_row1024) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    // Constraint: pedersen/input1_addr.
    tempvar value = (column3_row1034 - (column3_row10 + 1)) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    // Constraint: pedersen/output_value0.
    tempvar value = (column3_row523 - column5_row2045) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    // Constraint: pedersen/output_addr.
    tempvar value = (column3_row522 - (column3_row1034 + 1)) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    // Constraint: range_check_builtin/value.
    tempvar value = (range_check_builtin__value7_0 - column3_row75) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    // Constraint: range_check_builtin/addr_step.
    tempvar value = (column3_row202 - (column3_row74 + 1)) * domain20 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    // Constraint: range_check_builtin/init_addr.
    tempvar value = (column3_row74 - global_values.initial_range_check_addr) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    // Constraint: bitwise/init_var_pool_addr.
    tempvar value = (column3_row26 - global_values.initial_bitwise_addr) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    // Constraint: bitwise/step_var_pool_addr.
    tempvar value = (column3_row58 - (column3_row26 + 1)) * domain7 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    // Constraint: bitwise/x_or_y_addr.
    tempvar value = (column3_row42 - (column3_row122 + 1)) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    // Constraint: bitwise/next_var_pool_addr.
    tempvar value = (column3_row154 - (column3_row42 + 1)) * domain20 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    // Constraint: bitwise/partition.
    tempvar value = (bitwise__sum_var_0_0 + bitwise__sum_var_8_0 - column3_row27) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    // Constraint: bitwise/or_is_and_plus_xor.
    tempvar value = (column3_row43 - (column3_row91 + column3_row123)) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    // Constraint: bitwise/addition_is_xor_with_and.
    tempvar value = (
        column1_row0 + column1_row32 - (column1_row96 + column1_row64 + column1_row64)
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    // Constraint: bitwise/unique_unpacking192.
    tempvar value = ((column1_row88 + column1_row120) * 16 - column1_row1) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    // Constraint: bitwise/unique_unpacking193.
    tempvar value = ((column1_row90 + column1_row122) * 16 - column1_row65) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    // Constraint: bitwise/unique_unpacking194.
    tempvar value = ((column1_row92 + column1_row124) * 16 - column1_row33) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    // Constraint: bitwise/unique_unpacking195.
    tempvar value = ((column1_row94 + column1_row126) * 256 - column1_row97) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    return (res=total_sum);
}

func eval_oods_polynomial{range_check_ptr}(
    self: felt*,
    column_values: felt*,
    oods_values: felt*,
    constraint_coefficients: felt*,
    point: felt,
    oods_point: felt,
    trace_generator: felt,
) -> (res: felt) {
    alloc_locals;

    // Compute powers.
    let (local pow0) = pow(trace_generator, 0);
    let (local pow1) = pow(trace_generator, 1004);
    let (local pow2) = pow(trace_generator, 768);
    let (local pow3) = pow(trace_generator, 522);
    let (local pow4) = pow(trace_generator, 1);
    local pow5 = pow3 * pow4;  // pow(trace_generator, 523).
    local pow6 = pow4 * pow4;  // pow(trace_generator, 2).
    local pow7 = pow4 * pow6;  // pow(trace_generator, 3).
    local pow8 = pow4 * pow7;  // pow(trace_generator, 4).
    local pow9 = pow1 * pow8;  // pow(trace_generator, 1008).
    local pow10 = pow2 * pow8;  // pow(trace_generator, 772).
    local pow11 = pow4 * pow8;  // pow(trace_generator, 5).
    local pow12 = pow4 * pow11;  // pow(trace_generator, 6).
    local pow13 = pow4 * pow12;  // pow(trace_generator, 7).
    local pow14 = pow4 * pow13;  // pow(trace_generator, 8).
    local pow15 = pow4 * pow14;  // pow(trace_generator, 9).
    local pow16 = pow4 * pow15;  // pow(trace_generator, 10).
    local pow17 = pow4 * pow16;  // pow(trace_generator, 11).
    local pow18 = pow4 * pow17;  // pow(trace_generator, 12).
    local pow19 = pow4 * pow18;  // pow(trace_generator, 13).
    local pow20 = pow4 * pow19;  // pow(trace_generator, 14).
    local pow21 = pow4 * pow20;  // pow(trace_generator, 15).
    local pow22 = pow4 * pow21;  // pow(trace_generator, 16).
    local pow23 = pow2 * pow22;  // pow(trace_generator, 784).
    local pow24 = pow4 * pow22;  // pow(trace_generator, 17).
    local pow25 = pow1 * pow24;  // pow(trace_generator, 1021).
    local pow26 = pow4 * pow24;  // pow(trace_generator, 18).
    local pow27 = pow1 * pow26;  // pow(trace_generator, 1022).
    local pow28 = pow4 * pow27;  // pow(trace_generator, 1023).
    local pow29 = pow6 * pow26;  // pow(trace_generator, 20).
    local pow30 = pow6 * pow29;  // pow(trace_generator, 22).
    local pow31 = pow6 * pow30;  // pow(trace_generator, 24).
    local pow32 = pow4 * pow31;  // pow(trace_generator, 25).
    local pow33 = pow4 * pow32;  // pow(trace_generator, 26).
    local pow34 = pow1 * pow29;  // pow(trace_generator, 1024).
    local pow35 = pow25 * pow34;  // pow(trace_generator, 2045).
    local pow36 = pow4 * pow34;  // pow(trace_generator, 1025).
    local pow37 = pow6 * pow36;  // pow(trace_generator, 1027).
    local pow38 = pow4 * pow33;  // pow(trace_generator, 27).
    local pow39 = pow4 * pow38;  // pow(trace_generator, 28).
    local pow40 = pow6 * pow39;  // pow(trace_generator, 30).
    local pow41 = pow6 * pow40;  // pow(trace_generator, 32).
    local pow42 = pow4 * pow41;  // pow(trace_generator, 33).
    local pow43 = pow1 * pow40;  // pow(trace_generator, 1034).
    local pow44 = pow4 * pow43;  // pow(trace_generator, 1035).
    local pow45 = pow19 * pow35;  // pow(trace_generator, 2058).
    local pow46 = pow15 * pow42;  // pow(trace_generator, 42).
    local pow47 = pow4 * pow46;  // pow(trace_generator, 43).
    local pow48 = pow4 * pow47;  // pow(trace_generator, 44).
    local pow49 = pow20 * pow48;  // pow(trace_generator, 58).
    local pow50 = pow6 * pow49;  // pow(trace_generator, 60).
    local pow51 = pow2 * pow29;  // pow(trace_generator, 788).
    local pow52 = pow8 * pow50;  // pow(trace_generator, 64).
    local pow53 = pow4 * pow52;  // pow(trace_generator, 65).
    local pow54 = pow15 * pow53;  // pow(trace_generator, 74).
    local pow55 = pow4 * pow54;  // pow(trace_generator, 75).
    local pow56 = pow4 * pow55;  // pow(trace_generator, 76).
    local pow57 = pow18 * pow56;  // pow(trace_generator, 88).
    local pow58 = pow6 * pow57;  // pow(trace_generator, 90).
    local pow59 = pow4 * pow58;  // pow(trace_generator, 91).
    local pow60 = pow4 * pow59;  // pow(trace_generator, 92).
    local pow61 = pow6 * pow60;  // pow(trace_generator, 94).
    local pow62 = pow6 * pow61;  // pow(trace_generator, 96).
    local pow63 = pow4 * pow62;  // pow(trace_generator, 97).
    local pow64 = pow17 * pow63;  // pow(trace_generator, 108).
    local pow65 = pow18 * pow64;  // pow(trace_generator, 120).
    local pow66 = pow6 * pow65;  // pow(trace_generator, 122).
    local pow67 = pow4 * pow66;  // pow(trace_generator, 123).
    local pow68 = pow4 * pow67;  // pow(trace_generator, 124).
    local pow69 = pow6 * pow68;  // pow(trace_generator, 126).
    local pow70 = pow56 * pow69;  // pow(trace_generator, 202).
    local pow71 = pow39 * pow69;  // pow(trace_generator, 154).

    // Fetch columns.
    tempvar column0 = column_values[0];
    tempvar column1 = column_values[1];
    tempvar column2 = column_values[2];
    tempvar column3 = column_values[3];
    tempvar column4 = column_values[4];
    tempvar column5 = column_values[5];
    tempvar column6 = column_values[6];
    tempvar column7 = column_values[7];
    tempvar column8 = column_values[8];
    tempvar column9 = column_values[9];

    // Sum the OODS constraints on the trace polynomials.
    tempvar total_sum = 0;

    tempvar value = (column0 - oods_values[0]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[0] * value;

    tempvar value = (column0 - oods_values[1]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[1] * value;

    tempvar value = (column0 - oods_values[2]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[2] * value;

    tempvar value = (column0 - oods_values[3]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[3] * value;

    tempvar value = (column0 - oods_values[4]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[4] * value;

    tempvar value = (column0 - oods_values[5]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[5] * value;

    tempvar value = (column0 - oods_values[6]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[6] * value;

    tempvar value = (column0 - oods_values[7]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    tempvar value = (column0 - oods_values[8]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    tempvar value = (column0 - oods_values[9]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    tempvar value = (column0 - oods_values[10]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    tempvar value = (column0 - oods_values[11]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    tempvar value = (column0 - oods_values[12]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    tempvar value = (column0 - oods_values[13]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    tempvar value = (column0 - oods_values[14]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    tempvar value = (column0 - oods_values[15]) / (point - pow21 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    tempvar value = (column1 - oods_values[16]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    tempvar value = (column1 - oods_values[17]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    tempvar value = (column1 - oods_values[18]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    tempvar value = (column1 - oods_values[19]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    tempvar value = (column1 - oods_values[20]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    tempvar value = (column1 - oods_values[21]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[21] * value;

    tempvar value = (column1 - oods_values[22]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    tempvar value = (column1 - oods_values[23]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    tempvar value = (column1 - oods_values[24]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[24] * value;

    tempvar value = (column1 - oods_values[25]) / (point - pow22 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    tempvar value = (column1 - oods_values[26]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    tempvar value = (column1 - oods_values[27]) / (point - pow29 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    tempvar value = (column1 - oods_values[28]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    tempvar value = (column1 - oods_values[29]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    tempvar value = (column1 - oods_values[30]) / (point - pow33 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    tempvar value = (column1 - oods_values[31]) / (point - pow39 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    tempvar value = (column1 - oods_values[32]) / (point - pow40 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    tempvar value = (column1 - oods_values[33]) / (point - pow41 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    tempvar value = (column1 - oods_values[34]) / (point - pow42 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    tempvar value = (column1 - oods_values[35]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    tempvar value = (column1 - oods_values[36]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    tempvar value = (column1 - oods_values[37]) / (point - pow57 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    tempvar value = (column1 - oods_values[38]) / (point - pow58 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    tempvar value = (column1 - oods_values[39]) / (point - pow60 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    tempvar value = (column1 - oods_values[40]) / (point - pow61 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    tempvar value = (column1 - oods_values[41]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    tempvar value = (column1 - oods_values[42]) / (point - pow63 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    tempvar value = (column1 - oods_values[43]) / (point - pow65 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    tempvar value = (column1 - oods_values[44]) / (point - pow66 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    tempvar value = (column1 - oods_values[45]) / (point - pow68 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    tempvar value = (column1 - oods_values[46]) / (point - pow69 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    tempvar value = (column2 - oods_values[47]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    tempvar value = (column2 - oods_values[48]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    tempvar value = (column3 - oods_values[49]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    tempvar value = (column3 - oods_values[50]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    tempvar value = (column3 - oods_values[51]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    tempvar value = (column3 - oods_values[52]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    tempvar value = (column3 - oods_values[53]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    tempvar value = (column3 - oods_values[54]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    tempvar value = (column3 - oods_values[55]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    tempvar value = (column3 - oods_values[56]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    tempvar value = (column3 - oods_values[57]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    tempvar value = (column3 - oods_values[58]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    tempvar value = (column3 - oods_values[59]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    tempvar value = (column3 - oods_values[60]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    tempvar value = (column3 - oods_values[61]) / (point - pow22 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    tempvar value = (column3 - oods_values[62]) / (point - pow33 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    tempvar value = (column3 - oods_values[63]) / (point - pow38 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    tempvar value = (column3 - oods_values[64]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    tempvar value = (column3 - oods_values[65]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    tempvar value = (column3 - oods_values[66]) / (point - pow49 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    tempvar value = (column3 - oods_values[67]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    tempvar value = (column3 - oods_values[68]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    tempvar value = (column3 - oods_values[69]) / (point - pow59 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    tempvar value = (column3 - oods_values[70]) / (point - pow66 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    tempvar value = (column3 - oods_values[71]) / (point - pow67 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    tempvar value = (column3 - oods_values[72]) / (point - pow71 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    tempvar value = (column3 - oods_values[73]) / (point - pow70 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    tempvar value = (column3 - oods_values[74]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    tempvar value = (column3 - oods_values[75]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    tempvar value = (column3 - oods_values[76]) / (point - pow43 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    tempvar value = (column3 - oods_values[77]) / (point - pow44 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    tempvar value = (column3 - oods_values[78]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    tempvar value = (column4 - oods_values[79]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    tempvar value = (column4 - oods_values[80]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    tempvar value = (column4 - oods_values[81]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    tempvar value = (column4 - oods_values[82]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    tempvar value = (column5 - oods_values[83]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    tempvar value = (column5 - oods_values[84]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    tempvar value = (column5 - oods_values[85]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    tempvar value = (column5 - oods_values[86]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    tempvar value = (column5 - oods_values[87]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    tempvar value = (column5 - oods_values[88]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    tempvar value = (column5 - oods_values[89]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    tempvar value = (column5 - oods_values[90]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    tempvar value = (column5 - oods_values[91]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    tempvar value = (column5 - oods_values[92]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    tempvar value = (column5 - oods_values[93]) / (point - pow39 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    tempvar value = (column5 - oods_values[94]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    tempvar value = (column5 - oods_values[95]) / (point - pow50 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    tempvar value = (column5 - oods_values[96]) / (point - pow56 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    tempvar value = (column5 - oods_values[97]) / (point - pow60 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    tempvar value = (column5 - oods_values[98]) / (point - pow64 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    tempvar value = (column5 - oods_values[99]) / (point - pow68 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    tempvar value = (column5 - oods_values[100]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    tempvar value = (column5 - oods_values[101]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    tempvar value = (column5 - oods_values[102]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    tempvar value = (column5 - oods_values[103]) / (point - pow37 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    tempvar value = (column5 - oods_values[104]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    tempvar value = (column6 - oods_values[105]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    tempvar value = (column6 - oods_values[106]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    tempvar value = (column6 - oods_values[107]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    tempvar value = (column6 - oods_values[108]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    tempvar value = (column6 - oods_values[109]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    tempvar value = (column6 - oods_values[110]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    tempvar value = (column6 - oods_values[111]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    tempvar value = (column6 - oods_values[112]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    tempvar value = (column6 - oods_values[113]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    tempvar value = (column6 - oods_values[114]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    tempvar value = (column6 - oods_values[115]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    tempvar value = (column6 - oods_values[116]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    tempvar value = (column6 - oods_values[117]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    tempvar value = (column6 - oods_values[118]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    tempvar value = (column6 - oods_values[119]) / (point - pow23 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    tempvar value = (column6 - oods_values[120]) / (point - pow51 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    tempvar value = (column6 - oods_values[121]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    tempvar value = (column6 - oods_values[122]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    tempvar value = (column6 - oods_values[123]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    tempvar value = (column6 - oods_values[124]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    tempvar value = (column7 - oods_values[125]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    tempvar value = (column7 - oods_values[126]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    tempvar value = (column8 - oods_values[127]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    tempvar value = (column8 - oods_values[128]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    tempvar value = (column9 - oods_values[129]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    tempvar value = (column9 - oods_values[130]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    tempvar value = (column9 - oods_values[131]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    tempvar value = (column9 - oods_values[132]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    // Sum the OODS boundary constraints on the composition polynomials.
    let (oods_point_to_deg) = pow(oods_point, CONSTRAINT_DEGREE);

    tempvar value = (column_values[NUM_COLUMNS_FIRST + NUM_COLUMNS_SECOND] - oods_values[133]) / (
        point - oods_point_to_deg
    );
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

    tempvar value = (column_values[NUM_COLUMNS_FIRST + NUM_COLUMNS_SECOND + 1] - oods_values[134]) /
        (point - oods_point_to_deg);
    tempvar total_sum = total_sum + constraint_coefficients[134] * value;

    static_assert 135 == MASK_SIZE + CONSTRAINT_DEGREE;
    return (res=total_sum);
}
