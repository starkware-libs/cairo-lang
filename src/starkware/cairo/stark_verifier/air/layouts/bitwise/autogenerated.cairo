from starkware.cairo.stark_verifier.air.layouts.bitwise.global_values import GlobalValues
from starkware.cairo.stark_verifier.air.oods import OodsGlobalValues
from starkware.cairo.common.pow import pow

const N_CONSTRAINTS = 134;
const MASK_SIZE = 174;
const N_ORIGINAL_COLUMNS = 7;
const N_INTERACTION_COLUMNS = 3;
const PUBLIC_MEMORY_STEP = 16;
const HAS_DILUTED_POOL = 1;
const DILUTED_SPACING = 4;
const DILUTED_N_BITS = 16;
const PEDERSEN_BUILTIN_RATIO = 256;
const PEDERSEN_BUILTIN_REPETITIONS = 1;
const RC_BUILTIN_RATIO = 8;
const RC_N_PARTS = 8;
const ECDSA_BUILTIN_RATIO = 1024;
const ECDSA_BUILTIN_REPETITIONS = 1;
const ECDSA_ELEMENT_BITS = 251;
const ECDSA_ELEMENT_HEIGHT = 256;
const BITWISE__RATIO = 8;
const BITWISE__TOTAL_N_BITS = 251;
const HAS_OUTPUT_BUILTIN = 1;
const HAS_PEDERSEN_BUILTIN = 1;
const HAS_RANGE_CHECK_BUILTIN = 1;
const HAS_ECDSA_BUILTIN = 1;
const HAS_BITWISE_BUILTIN = 1;
const HAS_KECCAK_BUILTIN = 0;
const HAS_EC_OP_BUILTIN = 0;
const LAYOUT_CODE = 0x62697477697365;
const CONSTRAINT_DEGREE = 2;
const CPU_COMPONENT_HEIGHT = 16;
const LOG_CPU_COMPONENT_HEIGHT = 4;
const MEMORY_STEP = 2;
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
    let (local pow0) = pow(point, global_values.trace_length / 16384);
    local pow1 = pow0 * pow0;
    local pow2 = pow1 * pow1;
    local pow3 = pow2 * pow2;
    let (local pow4) = pow(point, global_values.trace_length / 128);
    local pow5 = pow4 * pow4;
    local pow6 = pow5 * pow5;
    local pow7 = pow6 * pow6;
    local pow8 = pow7 * pow7;
    local pow9 = pow8 * pow8;
    local pow10 = pow9 * pow9;
    local pow11 = pow10 * pow10;
    let (local pow12) = pow(trace_generator, global_values.trace_length / 64);
    local pow13 = pow12 * pow12;
    local pow14 = pow12 * pow13;
    local pow15 = pow12 * pow14;
    local pow16 = pow12 * pow15;
    local pow17 = pow12 * pow16;
    local pow18 = pow12 * pow17;
    local pow19 = pow12 * pow18;
    local pow20 = pow12 * pow19;
    local pow21 = pow12 * pow20;
    local pow22 = pow12 * pow21;
    local pow23 = pow12 * pow22;
    local pow24 = pow12 * pow23;
    local pow25 = pow12 * pow24;
    local pow26 = pow12 * pow25;
    let (local pow27) = pow(trace_generator, global_values.trace_length / 2);
    let (local pow28) = pow(trace_generator, 3 * global_values.trace_length / 4);
    local pow29 = pow23 * pow28;
    let (local pow30) = pow(trace_generator, 251 * global_values.trace_length / 256);
    local pow31 = pow14 * pow29;
    local pow32 = pow12 * pow30;
    let (local pow33) = pow(trace_generator, 16 * (global_values.trace_length / 16 - 1));
    let (local pow34) = pow(trace_generator, 2 * (global_values.trace_length / 2 - 1));
    let (local pow35) = pow(trace_generator, 4 * (global_values.trace_length / 4 - 1));
    let (local pow36) = pow(trace_generator, global_values.trace_length - 1);
    let (local pow37) = pow(trace_generator, 4096 * (global_values.trace_length / 4096 - 1));
    let (local pow38) = pow(trace_generator, 128 * (global_values.trace_length / 128 - 1));
    let (local pow39) = pow(trace_generator, 16384 * (global_values.trace_length / 16384 - 1));

    // Compute domains.
    tempvar domain0 = pow11 - 1;
    tempvar domain1 = pow10 - 1;
    tempvar domain2 = pow9 - 1;
    tempvar domain3 = pow8 - 1;
    tempvar domain4 = pow7 - pow29;
    tempvar domain5 = pow7 - 1;
    tempvar domain6 = pow6 - 1;
    tempvar domain7 = pow5 - 1;
    tempvar domain8 = pow4 - 1;
    tempvar domain9 = pow4 - pow28;
    tempvar domain10 = pow4 - pow12;
    tempvar domain10 = domain10 * (pow4 - pow13);
    tempvar domain10 = domain10 * (pow4 - pow14);
    tempvar domain10 = domain10 * (pow4 - pow15);
    tempvar domain10 = domain10 * (pow4 - pow16);
    tempvar domain10 = domain10 * (pow4 - pow17);
    tempvar domain10 = domain10 * (pow4 - pow18);
    tempvar domain10 = domain10 * (pow4 - pow19);
    tempvar domain10 = domain10 * (pow4 - pow20);
    tempvar domain10 = domain10 * (pow4 - pow21);
    tempvar domain10 = domain10 * (pow4 - pow22);
    tempvar domain10 = domain10 * (pow4 - pow23);
    tempvar domain10 = domain10 * (pow4 - pow24);
    tempvar domain10 = domain10 * (pow4 - pow25);
    tempvar domain10 = domain10 * (pow4 - pow26);
    tempvar domain10 = domain10 * (domain8);
    tempvar domain11 = pow3 - 1;
    tempvar domain12 = pow3 - pow32;
    tempvar domain13 = pow3 - pow31;
    tempvar domain14 = pow2 - pow27;
    tempvar domain15 = pow2 - 1;
    tempvar domain16 = pow1 - pow32;
    tempvar domain17 = pow1 - pow30;
    tempvar domain18 = pow1 - 1;
    tempvar domain19 = pow0 - pow32;
    tempvar domain20 = pow0 - pow30;
    tempvar domain21 = pow0 - 1;
    tempvar domain22 = point - pow33;
    tempvar domain23 = point - 1;
    tempvar domain24 = point - pow34;
    tempvar domain25 = point - pow35;
    tempvar domain26 = point - pow36;
    tempvar domain27 = point - pow37;
    tempvar domain28 = point - pow38;
    tempvar domain29 = point - pow39;

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
    tempvar column3_row1034 = mask_values[74];
    tempvar column3_row1035 = mask_values[75];
    tempvar column3_row2058 = mask_values[76];
    tempvar column3_row2059 = mask_values[77];
    tempvar column3_row3082 = mask_values[78];
    tempvar column3_row3083 = mask_values[79];
    tempvar column3_row4106 = mask_values[80];
    tempvar column3_row11274 = mask_values[81];
    tempvar column3_row11275 = mask_values[82];
    tempvar column3_row19466 = mask_values[83];
    tempvar column4_row0 = mask_values[84];
    tempvar column4_row1 = mask_values[85];
    tempvar column4_row2 = mask_values[86];
    tempvar column4_row3 = mask_values[87];
    tempvar column5_row0 = mask_values[88];
    tempvar column5_row1 = mask_values[89];
    tempvar column5_row2 = mask_values[90];
    tempvar column5_row3 = mask_values[91];
    tempvar column5_row4 = mask_values[92];
    tempvar column5_row5 = mask_values[93];
    tempvar column5_row6 = mask_values[94];
    tempvar column5_row7 = mask_values[95];
    tempvar column5_row8 = mask_values[96];
    tempvar column5_row9 = mask_values[97];
    tempvar column5_row11 = mask_values[98];
    tempvar column5_row12 = mask_values[99];
    tempvar column5_row13 = mask_values[100];
    tempvar column5_row28 = mask_values[101];
    tempvar column5_row44 = mask_values[102];
    tempvar column5_row60 = mask_values[103];
    tempvar column5_row76 = mask_values[104];
    tempvar column5_row92 = mask_values[105];
    tempvar column5_row108 = mask_values[106];
    tempvar column5_row124 = mask_values[107];
    tempvar column5_row1539 = mask_values[108];
    tempvar column5_row1547 = mask_values[109];
    tempvar column5_row1571 = mask_values[110];
    tempvar column5_row1579 = mask_values[111];
    tempvar column5_row2011 = mask_values[112];
    tempvar column5_row2019 = mask_values[113];
    tempvar column5_row2041 = mask_values[114];
    tempvar column5_row2045 = mask_values[115];
    tempvar column5_row2047 = mask_values[116];
    tempvar column5_row2049 = mask_values[117];
    tempvar column5_row2051 = mask_values[118];
    tempvar column5_row2053 = mask_values[119];
    tempvar column5_row4089 = mask_values[120];
    tempvar column6_row0 = mask_values[121];
    tempvar column6_row1 = mask_values[122];
    tempvar column6_row2 = mask_values[123];
    tempvar column6_row4 = mask_values[124];
    tempvar column6_row5 = mask_values[125];
    tempvar column6_row6 = mask_values[126];
    tempvar column6_row8 = mask_values[127];
    tempvar column6_row9 = mask_values[128];
    tempvar column6_row10 = mask_values[129];
    tempvar column6_row12 = mask_values[130];
    tempvar column6_row13 = mask_values[131];
    tempvar column6_row14 = mask_values[132];
    tempvar column6_row16 = mask_values[133];
    tempvar column6_row17 = mask_values[134];
    tempvar column6_row21 = mask_values[135];
    tempvar column6_row22 = mask_values[136];
    tempvar column6_row24 = mask_values[137];
    tempvar column6_row25 = mask_values[138];
    tempvar column6_row30 = mask_values[139];
    tempvar column6_row33 = mask_values[140];
    tempvar column6_row37 = mask_values[141];
    tempvar column6_row38 = mask_values[142];
    tempvar column6_row45 = mask_values[143];
    tempvar column6_row46 = mask_values[144];
    tempvar column6_row53 = mask_values[145];
    tempvar column6_row54 = mask_values[146];
    tempvar column6_row62 = mask_values[147];
    tempvar column6_row69 = mask_values[148];
    tempvar column6_row85 = mask_values[149];
    tempvar column6_row101 = mask_values[150];
    tempvar column6_row8169 = mask_values[151];
    tempvar column6_row8174 = mask_values[152];
    tempvar column6_row8177 = mask_values[153];
    tempvar column6_row8185 = mask_values[154];
    tempvar column6_row8190 = mask_values[155];
    tempvar column6_row8198 = mask_values[156];
    tempvar column6_row8214 = mask_values[157];
    tempvar column6_row16325 = mask_values[158];
    tempvar column6_row16333 = mask_values[159];
    tempvar column6_row16357 = mask_values[160];
    tempvar column6_row16361 = mask_values[161];
    tempvar column6_row16366 = mask_values[162];
    tempvar column6_row16373 = mask_values[163];
    tempvar column6_row16377 = mask_values[164];
    tempvar column6_row16382 = mask_values[165];
    tempvar column7_inter1_row0 = mask_values[166];
    tempvar column7_inter1_row1 = mask_values[167];
    tempvar column8_inter1_row0 = mask_values[168];
    tempvar column8_inter1_row1 = mask_values[169];
    tempvar column9_inter1_row0 = mask_values[170];
    tempvar column9_inter1_row1 = mask_values[171];
    tempvar column9_inter1_row2 = mask_values[172];
    tempvar column9_inter1_row5 = mask_values[173];

    // Compute intermediate values.
    tempvar cpu__decode__opcode_rc__bit_0 = column0_row0 - (column0_row1 + column0_row1);
    tempvar cpu__decode__opcode_rc__bit_2 = column0_row2 - (column0_row3 + column0_row3);
    tempvar cpu__decode__opcode_rc__bit_4 = column0_row4 - (column0_row5 + column0_row5);
    tempvar cpu__decode__opcode_rc__bit_3 = column0_row3 - (column0_row4 + column0_row4);
    tempvar cpu__decode__flag_op1_base_op0_0 = 1 - (
        cpu__decode__opcode_rc__bit_2 +
        cpu__decode__opcode_rc__bit_4 +
        cpu__decode__opcode_rc__bit_3
    );
    tempvar cpu__decode__opcode_rc__bit_5 = column0_row5 - (column0_row6 + column0_row6);
    tempvar cpu__decode__opcode_rc__bit_6 = column0_row6 - (column0_row7 + column0_row7);
    tempvar cpu__decode__opcode_rc__bit_9 = column0_row9 - (column0_row10 + column0_row10);
    tempvar cpu__decode__flag_res_op1_0 = 1 - (
        cpu__decode__opcode_rc__bit_5 +
        cpu__decode__opcode_rc__bit_6 +
        cpu__decode__opcode_rc__bit_9
    );
    tempvar cpu__decode__opcode_rc__bit_7 = column0_row7 - (column0_row8 + column0_row8);
    tempvar cpu__decode__opcode_rc__bit_8 = column0_row8 - (column0_row9 + column0_row9);
    tempvar cpu__decode__flag_pc_update_regular_0 = 1 - (
        cpu__decode__opcode_rc__bit_7 +
        cpu__decode__opcode_rc__bit_8 +
        cpu__decode__opcode_rc__bit_9
    );
    tempvar cpu__decode__opcode_rc__bit_12 = column0_row12 - (column0_row13 + column0_row13);
    tempvar cpu__decode__opcode_rc__bit_13 = column0_row13 - (column0_row14 + column0_row14);
    tempvar cpu__decode__fp_update_regular_0 = 1 - (
        cpu__decode__opcode_rc__bit_12 + cpu__decode__opcode_rc__bit_13
    );
    tempvar cpu__decode__opcode_rc__bit_1 = column0_row1 - (column0_row2 + column0_row2);
    tempvar npc_reg_0 = column3_row0 + cpu__decode__opcode_rc__bit_2 + 1;
    tempvar cpu__decode__opcode_rc__bit_10 = column0_row10 - (column0_row11 + column0_row11);
    tempvar cpu__decode__opcode_rc__bit_11 = column0_row11 - (column0_row12 + column0_row12);
    tempvar cpu__decode__opcode_rc__bit_14 = column0_row14 - (column0_row15 + column0_row15);
    tempvar memory__address_diff_0 = column4_row2 - column4_row0;
    tempvar rc16__diff_0 = column5_row6 - column5_row2;
    tempvar pedersen__hash0__ec_subset_sum__bit_0 = column5_row3 - (column5_row11 + column5_row11);
    tempvar pedersen__hash0__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash0__ec_subset_sum__bit_0;
    tempvar rc_builtin__value0_0 = column5_row12;
    tempvar rc_builtin__value1_0 = rc_builtin__value0_0 * global_values.offset_size + column5_row28;
    tempvar rc_builtin__value2_0 = rc_builtin__value1_0 * global_values.offset_size + column5_row44;
    tempvar rc_builtin__value3_0 = rc_builtin__value2_0 * global_values.offset_size + column5_row60;
    tempvar rc_builtin__value4_0 = rc_builtin__value3_0 * global_values.offset_size + column5_row76;
    tempvar rc_builtin__value5_0 = rc_builtin__value4_0 * global_values.offset_size + column5_row92;
    tempvar rc_builtin__value6_0 = rc_builtin__value5_0 * global_values.offset_size +
        column5_row108;
    tempvar rc_builtin__value7_0 = rc_builtin__value6_0 * global_values.offset_size +
        column5_row124;
    tempvar ecdsa__signature0__doubling_key__x_squared = column6_row6 * column6_row6;
    tempvar ecdsa__signature0__exponentiate_generator__bit_0 = column6_row21 - (
        column6_row85 + column6_row85
    );
    tempvar ecdsa__signature0__exponentiate_generator__bit_neg_0 = 1 -
        ecdsa__signature0__exponentiate_generator__bit_0;
    tempvar ecdsa__signature0__exponentiate_key__bit_0 = column6_row1 - (
        column6_row33 + column6_row33
    );
    tempvar ecdsa__signature0__exponentiate_key__bit_neg_0 = 1 -
        ecdsa__signature0__exponentiate_key__bit_0;
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

    // Constraint: cpu/decode/opcode_rc/bit.
    tempvar value = (
        cpu__decode__opcode_rc__bit_0 * cpu__decode__opcode_rc__bit_0 -
        cpu__decode__opcode_rc__bit_0
    ) * domain4 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[0] * value;

    // Constraint: cpu/decode/opcode_rc/zero.
    tempvar value = (column0_row0) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[1] * value;

    // Constraint: cpu/decode/opcode_rc_input.
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
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[2] * value;

    // Constraint: cpu/decode/flag_op1_base_op0_bit.
    tempvar value = (
        cpu__decode__flag_op1_base_op0_0 * cpu__decode__flag_op1_base_op0_0 -
        cpu__decode__flag_op1_base_op0_0
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[3] * value;

    // Constraint: cpu/decode/flag_res_op1_bit.
    tempvar value = (
        cpu__decode__flag_res_op1_0 * cpu__decode__flag_res_op1_0 - cpu__decode__flag_res_op1_0
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[4] * value;

    // Constraint: cpu/decode/flag_pc_update_regular_bit.
    tempvar value = (
        cpu__decode__flag_pc_update_regular_0 * cpu__decode__flag_pc_update_regular_0 -
        cpu__decode__flag_pc_update_regular_0
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[5] * value;

    // Constraint: cpu/decode/fp_update_regular_bit.
    tempvar value = (
        cpu__decode__fp_update_regular_0 * cpu__decode__fp_update_regular_0 -
        cpu__decode__fp_update_regular_0
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[6] * value;

    // Constraint: cpu/operands/mem_dst_addr.
    tempvar value = (
        column3_row8 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_rc__bit_0 * column6_row8 +
            (1 - cpu__decode__opcode_rc__bit_0) * column6_row0 +
            column5_row0
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    // Constraint: cpu/operands/mem0_addr.
    tempvar value = (
        column3_row4 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_rc__bit_1 * column6_row8 +
            (1 - cpu__decode__opcode_rc__bit_1) * column6_row0 +
            column5_row8
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    // Constraint: cpu/operands/mem1_addr.
    tempvar value = (
        column3_row12 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_rc__bit_2 * column3_row0 +
            cpu__decode__opcode_rc__bit_4 * column6_row0 +
            cpu__decode__opcode_rc__bit_3 * column6_row8 +
            cpu__decode__flag_op1_base_op0_0 * column3_row5 +
            column5_row4
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    // Constraint: cpu/operands/ops_mul.
    tempvar value = (column6_row4 - column3_row5 * column3_row13) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    // Constraint: cpu/operands/res.
    tempvar value = (
        (1 - cpu__decode__opcode_rc__bit_9) * column6_row12 -
        (
            cpu__decode__opcode_rc__bit_5 * (column3_row5 + column3_row13) +
            cpu__decode__opcode_rc__bit_6 * column6_row4 +
            cpu__decode__flag_res_op1_0 * column3_row13
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    // Constraint: cpu/update_registers/update_pc/tmp0.
    tempvar value = (column6_row2 - cpu__decode__opcode_rc__bit_9 * column3_row9) * domain22 /
        domain5;
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    // Constraint: cpu/update_registers/update_pc/tmp1.
    tempvar value = (column6_row10 - column6_row2 * column6_row12) * domain22 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_negative.
    tempvar value = (
        (1 - cpu__decode__opcode_rc__bit_9) * column3_row16 +
        column6_row2 * (column3_row16 - (column3_row0 + column3_row13)) -
        (
            cpu__decode__flag_pc_update_regular_0 * npc_reg_0 +
            cpu__decode__opcode_rc__bit_7 * column6_row12 +
            cpu__decode__opcode_rc__bit_8 * (column3_row0 + column6_row12)
        )
    ) * domain22 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_positive.
    tempvar value = (
        (column6_row10 - cpu__decode__opcode_rc__bit_9) * (column3_row16 - npc_reg_0)
    ) * domain22 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    // Constraint: cpu/update_registers/update_ap/ap_update.
    tempvar value = (
        column6_row16 -
        (
            column6_row0 +
            cpu__decode__opcode_rc__bit_10 * column6_row12 +
            cpu__decode__opcode_rc__bit_11 +
            cpu__decode__opcode_rc__bit_12 * 2
        )
    ) * domain22 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    // Constraint: cpu/update_registers/update_fp/fp_update.
    tempvar value = (
        column6_row24 -
        (
            cpu__decode__fp_update_regular_0 * column6_row8 +
            cpu__decode__opcode_rc__bit_13 * column3_row9 +
            cpu__decode__opcode_rc__bit_12 * (column6_row0 + 2)
        )
    ) * domain22 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    // Constraint: cpu/opcodes/call/push_fp.
    tempvar value = (cpu__decode__opcode_rc__bit_12 * (column3_row9 - column6_row8)) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    // Constraint: cpu/opcodes/call/push_pc.
    tempvar value = (
        cpu__decode__opcode_rc__bit_12 * (
            column3_row5 - (column3_row0 + cpu__decode__opcode_rc__bit_2 + 1)
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    // Constraint: cpu/opcodes/call/off0.
    tempvar value = (
        cpu__decode__opcode_rc__bit_12 * (column5_row0 - global_values.half_offset_size)
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    // Constraint: cpu/opcodes/call/off1.
    tempvar value = (
        cpu__decode__opcode_rc__bit_12 * (column5_row8 - (global_values.half_offset_size + 1))
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[21] * value;

    // Constraint: cpu/opcodes/call/flags.
    tempvar value = (
        cpu__decode__opcode_rc__bit_12 * (
            cpu__decode__opcode_rc__bit_12 +
            cpu__decode__opcode_rc__bit_12 +
            1 +
            1 -
            (cpu__decode__opcode_rc__bit_0 + cpu__decode__opcode_rc__bit_1 + 4)
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    // Constraint: cpu/opcodes/ret/off0.
    tempvar value = (
        cpu__decode__opcode_rc__bit_13 * (column5_row0 + 2 - global_values.half_offset_size)
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    // Constraint: cpu/opcodes/ret/off2.
    tempvar value = (
        cpu__decode__opcode_rc__bit_13 * (column5_row4 + 1 - global_values.half_offset_size)
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[24] * value;

    // Constraint: cpu/opcodes/ret/flags.
    tempvar value = (
        cpu__decode__opcode_rc__bit_13 * (
            cpu__decode__opcode_rc__bit_7 +
            cpu__decode__opcode_rc__bit_0 +
            cpu__decode__opcode_rc__bit_3 +
            cpu__decode__flag_res_op1_0 -
            4
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    // Constraint: cpu/opcodes/assert_eq/assert_eq.
    tempvar value = (cpu__decode__opcode_rc__bit_14 * (column3_row9 - column6_row12)) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    // Constraint: initial_ap.
    tempvar value = (column6_row0 - global_values.initial_ap) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    // Constraint: initial_fp.
    tempvar value = (column6_row8 - global_values.initial_ap) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    // Constraint: initial_pc.
    tempvar value = (column3_row0 - global_values.initial_pc) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    // Constraint: final_ap.
    tempvar value = (column6_row0 - global_values.final_ap) / domain22;
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    // Constraint: final_fp.
    tempvar value = (column6_row8 - global_values.initial_ap) / domain22;
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    // Constraint: final_pc.
    tempvar value = (column3_row0 - global_values.final_pc) / domain22;
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
    ) / domain23;
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
    ) * domain24 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    // Constraint: memory/multi_column_perm/perm/last.
    tempvar value = (
        column9_inter1_row0 - global_values.memory__multi_column_perm__perm__public_memory_prod
    ) / domain24;
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    // Constraint: memory/diff_is_bit.
    tempvar value = (memory__address_diff_0 * memory__address_diff_0 - memory__address_diff_0) *
        domain24 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    // Constraint: memory/is_func.
    tempvar value = ((memory__address_diff_0 - 1) * (column4_row1 - column4_row3)) * domain24 /
        domain1;
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    // Constraint: memory/initial_addr.
    tempvar value = (column4_row0 - 1) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    // Constraint: public_memory_addr_zero.
    tempvar value = (column3_row2) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    // Constraint: public_memory_value_zero.
    tempvar value = (column3_row3) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    // Constraint: rc16/perm/init0.
    tempvar value = (
        (global_values.rc16__perm__interaction_elm - column5_row2) * column9_inter1_row1 +
        column5_row0 -
        global_values.rc16__perm__interaction_elm
    ) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    // Constraint: rc16/perm/step0.
    tempvar value = (
        (global_values.rc16__perm__interaction_elm - column5_row6) * column9_inter1_row5 -
        (global_values.rc16__perm__interaction_elm - column5_row4) * column9_inter1_row1
    ) * domain25 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    // Constraint: rc16/perm/last.
    tempvar value = (column9_inter1_row1 - global_values.rc16__perm__public_memory_prod) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    // Constraint: rc16/diff_is_bit.
    tempvar value = (rc16__diff_0 * rc16__diff_0 - rc16__diff_0) * domain25 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    // Constraint: rc16/minimum.
    tempvar value = (column5_row2 - global_values.rc_min) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    // Constraint: rc16/maximum.
    tempvar value = (column5_row2 - global_values.rc_max) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    // Constraint: diluted_check/permutation/init0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column2_row0) *
        column8_inter1_row0 +
        column1_row0 -
        global_values.diluted_check__permutation__interaction_elm
    ) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    // Constraint: diluted_check/permutation/step0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column2_row1) *
        column8_inter1_row1 -
        (global_values.diluted_check__permutation__interaction_elm - column1_row1) *
        column8_inter1_row0
    ) * domain26 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    // Constraint: diluted_check/permutation/last.
    tempvar value = (
        column8_inter1_row0 - global_values.diluted_check__permutation__public_memory_prod
    ) / domain26;
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    // Constraint: diluted_check/init.
    tempvar value = (column7_inter1_row0 - 1) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    // Constraint: diluted_check/first_element.
    tempvar value = (column2_row0 - global_values.diluted_check__first_elm) / domain23;
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
    ) * domain26 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    // Constraint: diluted_check/last.
    tempvar value = (column7_inter1_row0 - global_values.diluted_check__final_cum_val) / domain26;
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column6_row45 * (column5_row3 - (column5_row11 + column5_row11))) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column6_row45 * (
            column5_row11 -
            3138550867693340381917894711603833208051177722232017256448 * column5_row1539
        )
    ) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column6_row45 - column5_row2047 * (column5_row1539 - (column5_row1547 + column5_row1547))
    ) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column5_row2047 * (column5_row1547 - 8 * column5_row1571)) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column5_row2047 -
        (column5_row2011 - (column5_row2019 + column5_row2019)) * (
            column5_row1571 - (column5_row1579 + column5_row1579)
        )
    ) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column5_row2011 - (column5_row2019 + column5_row2019)) * (
            column5_row1579 - 18014398509481984 * column5_row2011
        )
    ) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (pedersen__hash0__ec_subset_sum__bit_0 - 1)
    ) * domain12 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_extraction_end.
    tempvar value = (column5_row3) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/zeros_tail.
    tempvar value = (column5_row3) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column5_row5 - global_values.pedersen__points__y) -
        column5_row7 * (column5_row1 - global_values.pedersen__points__x)
    ) * domain12 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/x.
    tempvar value = (
        column5_row7 * column5_row7 -
        pedersen__hash0__ec_subset_sum__bit_0 * (
            column5_row1 + global_values.pedersen__points__x + column5_row9
        )
    ) * domain12 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column5_row5 + column5_row13) -
        column5_row7 * (column5_row1 - column5_row9)
    ) * domain12 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column5_row9 - column5_row1)) *
        domain12 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column5_row13 - column5_row5)) *
        domain12 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    // Constraint: pedersen/hash0/copy_point/x.
    tempvar value = (column5_row2049 - column5_row2041) * domain14 / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    // Constraint: pedersen/hash0/copy_point/y.
    tempvar value = (column5_row2053 - column5_row2045) * domain14 / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    // Constraint: pedersen/hash0/init/x.
    tempvar value = (column5_row1 - global_values.pedersen__shift_point.x) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    // Constraint: pedersen/hash0/init/y.
    tempvar value = (column5_row5 - global_values.pedersen__shift_point.y) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    // Constraint: pedersen/input0_value0.
    tempvar value = (column3_row11 - column5_row3) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    // Constraint: pedersen/input0_addr.
    tempvar value = (column3_row4106 - (column3_row1034 + 1)) * domain27 / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    // Constraint: pedersen/init_addr.
    tempvar value = (column3_row10 - global_values.initial_pedersen_addr) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    // Constraint: pedersen/input1_value0.
    tempvar value = (column3_row2059 - column5_row2051) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    // Constraint: pedersen/input1_addr.
    tempvar value = (column3_row2058 - (column3_row10 + 1)) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    // Constraint: pedersen/output_value0.
    tempvar value = (column3_row1035 - column5_row4089) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    // Constraint: pedersen/output_addr.
    tempvar value = (column3_row1034 - (column3_row2058 + 1)) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    // Constraint: rc_builtin/value.
    tempvar value = (rc_builtin__value7_0 - column3_row75) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    // Constraint: rc_builtin/addr_step.
    tempvar value = (column3_row202 - (column3_row74 + 1)) * domain28 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    // Constraint: rc_builtin/init_addr.
    tempvar value = (column3_row74 - global_values.initial_rc_addr) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    // Constraint: ecdsa/signature0/doubling_key/slope.
    tempvar value = (
        ecdsa__signature0__doubling_key__x_squared +
        ecdsa__signature0__doubling_key__x_squared +
        ecdsa__signature0__doubling_key__x_squared +
        global_values.ecdsa__sig_config.alpha -
        (column6_row22 + column6_row22) * column6_row17
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    // Constraint: ecdsa/signature0/doubling_key/x.
    tempvar value = (
        column6_row17 * column6_row17 - (column6_row6 + column6_row6 + column6_row38)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    // Constraint: ecdsa/signature0/doubling_key/y.
    tempvar value = (
        column6_row22 + column6_row54 - column6_row17 * (column6_row6 - column6_row38)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/booleanity_test.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            ecdsa__signature0__exponentiate_generator__bit_0 - 1
        )
    ) * domain19 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/bit_extraction_end.
    tempvar value = (column6_row21) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/zeros_tail.
    tempvar value = (column6_row21) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/slope.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            column6_row37 - global_values.ecdsa__generator_points__y
        ) -
        column6_row53 * (column6_row5 - global_values.ecdsa__generator_points__x)
    ) * domain19 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/x.
    tempvar value = (
        column6_row53 * column6_row53 -
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            column6_row5 + global_values.ecdsa__generator_points__x + column6_row69
        )
    ) * domain19 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (column6_row37 + column6_row101) -
        column6_row53 * (column6_row5 - column6_row69)
    ) * domain19 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/x_diff_inv.
    tempvar value = (
        column6_row13 * (column6_row5 - global_values.ecdsa__generator_points__x) - 1
    ) * domain19 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/copy_point/x.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_neg_0 * (column6_row69 - column6_row5)
    ) * domain19 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/copy_point/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_neg_0 * (column6_row101 - column6_row37)
    ) * domain19 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/booleanity_test.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (
            ecdsa__signature0__exponentiate_key__bit_0 - 1
        )
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/bit_extraction_end.
    tempvar value = (column6_row1) / domain17;
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/zeros_tail.
    tempvar value = (column6_row1) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/slope.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (column6_row30 - column6_row22) -
        column6_row9 * (column6_row14 - column6_row6)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/x.
    tempvar value = (
        column6_row9 * column6_row9 -
        ecdsa__signature0__exponentiate_key__bit_0 * (column6_row14 + column6_row6 + column6_row46)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (column6_row30 + column6_row62) -
        column6_row9 * (column6_row14 - column6_row46)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/x_diff_inv.
    tempvar value = (column6_row25 * (column6_row14 - column6_row6) - 1) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/copy_point/x.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_neg_0 * (column6_row46 - column6_row14)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/copy_point/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_neg_0 * (column6_row62 - column6_row30)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    // Constraint: ecdsa/signature0/init_gen/x.
    tempvar value = (column6_row5 - global_values.ecdsa__sig_config.shift_point.x) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    // Constraint: ecdsa/signature0/init_gen/y.
    tempvar value = (column6_row37 + global_values.ecdsa__sig_config.shift_point.y) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    // Constraint: ecdsa/signature0/init_key/x.
    tempvar value = (column6_row14 - global_values.ecdsa__sig_config.shift_point.x) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    // Constraint: ecdsa/signature0/init_key/y.
    tempvar value = (column6_row30 - global_values.ecdsa__sig_config.shift_point.y) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    // Constraint: ecdsa/signature0/add_results/slope.
    tempvar value = (
        column6_row16357 -
        (column6_row8190 + column6_row16373 * (column6_row16325 - column6_row8174))
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    // Constraint: ecdsa/signature0/add_results/x.
    tempvar value = (
        column6_row16373 * column6_row16373 - (column6_row16325 + column6_row8174 + column6_row8198)
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    // Constraint: ecdsa/signature0/add_results/y.
    tempvar value = (
        column6_row16357 + column6_row8214 - column6_row16373 * (column6_row16325 - column6_row8198)
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    // Constraint: ecdsa/signature0/add_results/x_diff_inv.
    tempvar value = (column6_row16333 * (column6_row16325 - column6_row8174) - 1) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    // Constraint: ecdsa/signature0/extract_r/slope.
    tempvar value = (
        column6_row16382 +
        global_values.ecdsa__sig_config.shift_point.y -
        column6_row8169 * (column6_row16366 - global_values.ecdsa__sig_config.shift_point.x)
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    // Constraint: ecdsa/signature0/extract_r/x.
    tempvar value = (
        column6_row8169 * column6_row8169 -
        (column6_row16366 + global_values.ecdsa__sig_config.shift_point.x + column6_row1)
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    // Constraint: ecdsa/signature0/extract_r/x_diff_inv.
    tempvar value = (
        column6_row16361 * (column6_row16366 - global_values.ecdsa__sig_config.shift_point.x) - 1
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    // Constraint: ecdsa/signature0/z_nonzero.
    tempvar value = (column6_row21 * column6_row8185 - 1) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    // Constraint: ecdsa/signature0/r_and_w_nonzero.
    tempvar value = (column6_row1 * column6_row8177 - 1) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    // Constraint: ecdsa/signature0/q_on_curve/x_squared.
    tempvar value = (column6_row16377 - column6_row6 * column6_row6) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    // Constraint: ecdsa/signature0/q_on_curve/on_curve.
    tempvar value = (
        column6_row22 * column6_row22 -
        (
            column6_row6 * column6_row16377 +
            global_values.ecdsa__sig_config.alpha * column6_row6 +
            global_values.ecdsa__sig_config.beta
        )
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    // Constraint: ecdsa/init_addr.
    tempvar value = (column3_row3082 - global_values.initial_ecdsa_addr) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    // Constraint: ecdsa/message_addr.
    tempvar value = (column3_row11274 - (column3_row3082 + 1)) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    // Constraint: ecdsa/pubkey_addr.
    tempvar value = (column3_row19466 - (column3_row11274 + 1)) * domain29 / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    // Constraint: ecdsa/message_value0.
    tempvar value = (column3_row11275 - column6_row21) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    // Constraint: ecdsa/pubkey_value0.
    tempvar value = (column3_row3083 - column6_row6) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    // Constraint: bitwise/init_var_pool_addr.
    tempvar value = (column3_row26 - global_values.initial_bitwise_addr) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    // Constraint: bitwise/step_var_pool_addr.
    tempvar value = (column3_row58 - (column3_row26 + 1)) * domain9 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    // Constraint: bitwise/x_or_y_addr.
    tempvar value = (column3_row42 - (column3_row122 + 1)) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    // Constraint: bitwise/next_var_pool_addr.
    tempvar value = (column3_row154 - (column3_row42 + 1)) * domain28 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    // Constraint: bitwise/partition.
    tempvar value = (bitwise__sum_var_0_0 + bitwise__sum_var_8_0 - column3_row27) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    // Constraint: bitwise/or_is_and_plus_xor.
    tempvar value = (column3_row43 - (column3_row91 + column3_row123)) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    // Constraint: bitwise/addition_is_xor_with_and.
    tempvar value = (
        column1_row0 + column1_row32 - (column1_row96 + column1_row64 + column1_row64)
    ) / domain10;
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    // Constraint: bitwise/unique_unpacking192.
    tempvar value = ((column1_row88 + column1_row120) * 16 - column1_row1) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    // Constraint: bitwise/unique_unpacking193.
    tempvar value = ((column1_row90 + column1_row122) * 16 - column1_row65) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    // Constraint: bitwise/unique_unpacking194.
    tempvar value = ((column1_row92 + column1_row124) * 16 - column1_row33) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    // Constraint: bitwise/unique_unpacking195.
    tempvar value = ((column1_row94 + column1_row126) * 256 - column1_row97) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

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
    global_values: OodsGlobalValues*,
) -> (res: felt) {
    alloc_locals;

    // Compute powers.
    let (local pow0) = pow(trace_generator, 0);
    let (local pow1) = pow(trace_generator, 1);
    local pow2 = pow1 * pow1;
    local pow3 = pow1 * pow2;
    local pow4 = pow1 * pow3;
    local pow5 = pow1 * pow4;
    local pow6 = pow1 * pow5;
    local pow7 = pow1 * pow6;
    local pow8 = pow1 * pow7;
    local pow9 = pow1 * pow8;
    local pow10 = pow1 * pow9;
    local pow11 = pow1 * pow10;
    local pow12 = pow1 * pow11;
    local pow13 = pow1 * pow12;
    local pow14 = pow1 * pow13;
    local pow15 = pow1 * pow14;
    local pow16 = pow1 * pow15;
    local pow17 = pow1 * pow16;
    local pow18 = pow1 * pow17;
    local pow19 = pow2 * pow18;
    local pow20 = pow1 * pow19;
    local pow21 = pow1 * pow20;
    local pow22 = pow2 * pow21;
    local pow23 = pow1 * pow22;
    local pow24 = pow1 * pow23;
    local pow25 = pow1 * pow24;
    local pow26 = pow1 * pow25;
    local pow27 = pow2 * pow26;
    local pow28 = pow2 * pow27;
    local pow29 = pow1 * pow28;
    local pow30 = pow4 * pow29;
    local pow31 = pow1 * pow30;
    local pow32 = pow4 * pow31;
    local pow33 = pow1 * pow32;
    local pow34 = pow1 * pow33;
    local pow35 = pow1 * pow34;
    local pow36 = pow1 * pow35;
    local pow37 = pow7 * pow36;
    local pow38 = pow1 * pow37;
    local pow39 = pow4 * pow38;
    local pow40 = pow2 * pow39;
    local pow41 = pow2 * pow40;
    local pow42 = pow2 * pow41;
    local pow43 = pow1 * pow42;
    local pow44 = pow4 * pow43;
    local pow45 = pow5 * pow44;
    local pow46 = pow1 * pow45;
    local pow47 = pow1 * pow46;
    local pow48 = pow9 * pow47;
    local pow49 = pow3 * pow48;
    local pow50 = pow2 * pow49;
    local pow51 = pow1 * pow50;
    local pow52 = pow1 * pow51;
    local pow53 = pow2 * pow52;
    local pow54 = pow2 * pow53;
    local pow55 = pow1 * pow54;
    local pow56 = pow4 * pow55;
    local pow57 = pow7 * pow56;
    local pow58 = pow12 * pow57;
    local pow59 = pow2 * pow58;
    local pow60 = pow1 * pow59;
    local pow61 = pow1 * pow60;
    local pow62 = pow2 * pow61;
    local pow63 = pow26 * pow62;
    local pow64 = pow47 * pow62;
    let (local pow65) = pow(trace_generator, 1034);
    local pow66 = pow1 * pow65;
    let (local pow67) = pow(trace_generator, 1539);
    local pow68 = pow8 * pow67;
    local pow69 = pow22 * pow68;
    local pow70 = pow8 * pow69;
    let (local pow71) = pow(trace_generator, 2011);
    local pow72 = pow8 * pow71;
    local pow73 = pow21 * pow72;
    local pow74 = pow4 * pow73;
    local pow75 = pow2 * pow74;
    local pow76 = pow2 * pow75;
    local pow77 = pow2 * pow76;
    local pow78 = pow2 * pow77;
    local pow79 = pow5 * pow78;
    local pow80 = pow1 * pow79;
    local pow81 = pow66 * pow75;
    local pow82 = pow1 * pow81;
    let (local pow83) = pow(trace_generator, 4089);
    local pow84 = pow17 * pow83;
    let (local pow85) = pow(trace_generator, 8169);
    local pow86 = pow5 * pow85;
    local pow87 = pow3 * pow86;
    local pow88 = pow8 * pow87;
    local pow89 = pow5 * pow88;
    local pow90 = pow8 * pow89;
    local pow91 = pow16 * pow90;
    let (local pow92) = pow(trace_generator, 11274);
    local pow93 = pow1 * pow92;
    let (local pow94) = pow(trace_generator, 16325);
    local pow95 = pow8 * pow94;
    local pow96 = pow22 * pow95;
    local pow97 = pow4 * pow96;
    local pow98 = pow5 * pow97;
    local pow99 = pow7 * pow98;
    local pow100 = pow4 * pow99;
    local pow101 = pow5 * pow100;
    let (local pow102) = pow(trace_generator, 19466);

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

    tempvar value = (column0 - oods_values[1]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[1] * value;

    tempvar value = (column0 - oods_values[2]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[2] * value;

    tempvar value = (column0 - oods_values[3]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[3] * value;

    tempvar value = (column0 - oods_values[4]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[4] * value;

    tempvar value = (column0 - oods_values[5]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[5] * value;

    tempvar value = (column0 - oods_values[6]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[6] * value;

    tempvar value = (column0 - oods_values[7]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    tempvar value = (column0 - oods_values[8]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    tempvar value = (column0 - oods_values[9]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    tempvar value = (column0 - oods_values[10]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    tempvar value = (column0 - oods_values[11]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    tempvar value = (column0 - oods_values[12]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    tempvar value = (column0 - oods_values[13]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    tempvar value = (column0 - oods_values[14]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    tempvar value = (column0 - oods_values[15]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    tempvar value = (column1 - oods_values[16]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    tempvar value = (column1 - oods_values[17]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    tempvar value = (column1 - oods_values[18]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    tempvar value = (column1 - oods_values[19]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    tempvar value = (column1 - oods_values[20]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    tempvar value = (column1 - oods_values[21]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[21] * value;

    tempvar value = (column1 - oods_values[22]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    tempvar value = (column1 - oods_values[23]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    tempvar value = (column1 - oods_values[24]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[24] * value;

    tempvar value = (column1 - oods_values[25]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    tempvar value = (column1 - oods_values[26]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    tempvar value = (column1 - oods_values[27]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    tempvar value = (column1 - oods_values[28]) / (point - pow21 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    tempvar value = (column1 - oods_values[29]) / (point - pow22 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    tempvar value = (column1 - oods_values[30]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    tempvar value = (column1 - oods_values[31]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    tempvar value = (column1 - oods_values[32]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    tempvar value = (column1 - oods_values[33]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    tempvar value = (column1 - oods_values[34]) / (point - pow29 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    tempvar value = (column1 - oods_values[35]) / (point - pow42 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    tempvar value = (column1 - oods_values[36]) / (point - pow43 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    tempvar value = (column1 - oods_values[37]) / (point - pow49 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    tempvar value = (column1 - oods_values[38]) / (point - pow50 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    tempvar value = (column1 - oods_values[39]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    tempvar value = (column1 - oods_values[40]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    tempvar value = (column1 - oods_values[41]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    tempvar value = (column1 - oods_values[42]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    tempvar value = (column1 - oods_values[43]) / (point - pow58 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    tempvar value = (column1 - oods_values[44]) / (point - pow59 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    tempvar value = (column1 - oods_values[45]) / (point - pow61 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    tempvar value = (column1 - oods_values[46]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    tempvar value = (column2 - oods_values[47]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    tempvar value = (column2 - oods_values[48]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    tempvar value = (column3 - oods_values[49]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    tempvar value = (column3 - oods_values[50]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    tempvar value = (column3 - oods_values[51]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    tempvar value = (column3 - oods_values[52]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    tempvar value = (column3 - oods_values[53]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    tempvar value = (column3 - oods_values[54]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    tempvar value = (column3 - oods_values[55]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    tempvar value = (column3 - oods_values[56]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    tempvar value = (column3 - oods_values[57]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    tempvar value = (column3 - oods_values[58]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    tempvar value = (column3 - oods_values[59]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    tempvar value = (column3 - oods_values[60]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    tempvar value = (column3 - oods_values[61]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    tempvar value = (column3 - oods_values[62]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    tempvar value = (column3 - oods_values[63]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    tempvar value = (column3 - oods_values[64]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    tempvar value = (column3 - oods_values[65]) / (point - pow33 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    tempvar value = (column3 - oods_values[66]) / (point - pow39 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    tempvar value = (column3 - oods_values[67]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    tempvar value = (column3 - oods_values[68]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    tempvar value = (column3 - oods_values[69]) / (point - pow51 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    tempvar value = (column3 - oods_values[70]) / (point - pow59 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    tempvar value = (column3 - oods_values[71]) / (point - pow60 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    tempvar value = (column3 - oods_values[72]) / (point - pow63 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    tempvar value = (column3 - oods_values[73]) / (point - pow64 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    tempvar value = (column3 - oods_values[74]) / (point - pow65 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    tempvar value = (column3 - oods_values[75]) / (point - pow66 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    tempvar value = (column3 - oods_values[76]) / (point - pow79 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    tempvar value = (column3 - oods_values[77]) / (point - pow80 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    tempvar value = (column3 - oods_values[78]) / (point - pow81 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    tempvar value = (column3 - oods_values[79]) / (point - pow82 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    tempvar value = (column3 - oods_values[80]) / (point - pow84 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    tempvar value = (column3 - oods_values[81]) / (point - pow92 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    tempvar value = (column3 - oods_values[82]) / (point - pow93 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    tempvar value = (column3 - oods_values[83]) / (point - pow102 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    tempvar value = (column4 - oods_values[84]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    tempvar value = (column4 - oods_values[85]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    tempvar value = (column4 - oods_values[86]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    tempvar value = (column4 - oods_values[87]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    tempvar value = (column5 - oods_values[88]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    tempvar value = (column5 - oods_values[89]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    tempvar value = (column5 - oods_values[90]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    tempvar value = (column5 - oods_values[91]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    tempvar value = (column5 - oods_values[92]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    tempvar value = (column5 - oods_values[93]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    tempvar value = (column5 - oods_values[94]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    tempvar value = (column5 - oods_values[95]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    tempvar value = (column5 - oods_values[96]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    tempvar value = (column5 - oods_values[97]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    tempvar value = (column5 - oods_values[98]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    tempvar value = (column5 - oods_values[99]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    tempvar value = (column5 - oods_values[100]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    tempvar value = (column5 - oods_values[101]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    tempvar value = (column5 - oods_values[102]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    tempvar value = (column5 - oods_values[103]) / (point - pow40 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    tempvar value = (column5 - oods_values[104]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    tempvar value = (column5 - oods_values[105]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    tempvar value = (column5 - oods_values[106]) / (point - pow57 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    tempvar value = (column5 - oods_values[107]) / (point - pow61 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    tempvar value = (column5 - oods_values[108]) / (point - pow67 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    tempvar value = (column5 - oods_values[109]) / (point - pow68 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    tempvar value = (column5 - oods_values[110]) / (point - pow69 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    tempvar value = (column5 - oods_values[111]) / (point - pow70 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    tempvar value = (column5 - oods_values[112]) / (point - pow71 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    tempvar value = (column5 - oods_values[113]) / (point - pow72 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    tempvar value = (column5 - oods_values[114]) / (point - pow73 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    tempvar value = (column5 - oods_values[115]) / (point - pow74 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    tempvar value = (column5 - oods_values[116]) / (point - pow75 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    tempvar value = (column5 - oods_values[117]) / (point - pow76 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    tempvar value = (column5 - oods_values[118]) / (point - pow77 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    tempvar value = (column5 - oods_values[119]) / (point - pow78 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    tempvar value = (column5 - oods_values[120]) / (point - pow83 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    tempvar value = (column6 - oods_values[121]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    tempvar value = (column6 - oods_values[122]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    tempvar value = (column6 - oods_values[123]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    tempvar value = (column6 - oods_values[124]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    tempvar value = (column6 - oods_values[125]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    tempvar value = (column6 - oods_values[126]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    tempvar value = (column6 - oods_values[127]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    tempvar value = (column6 - oods_values[128]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    tempvar value = (column6 - oods_values[129]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    tempvar value = (column6 - oods_values[130]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    tempvar value = (column6 - oods_values[131]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    tempvar value = (column6 - oods_values[132]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    tempvar value = (column6 - oods_values[133]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

    tempvar value = (column6 - oods_values[134]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[134] * value;

    tempvar value = (column6 - oods_values[135]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[135] * value;

    tempvar value = (column6 - oods_values[136]) / (point - pow21 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[136] * value;

    tempvar value = (column6 - oods_values[137]) / (point - pow22 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[137] * value;

    tempvar value = (column6 - oods_values[138]) / (point - pow23 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[138] * value;

    tempvar value = (column6 - oods_values[139]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[139] * value;

    tempvar value = (column6 - oods_values[140]) / (point - pow29 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[140] * value;

    tempvar value = (column6 - oods_values[141]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[141] * value;

    tempvar value = (column6 - oods_values[142]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[142] * value;

    tempvar value = (column6 - oods_values[143]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[143] * value;

    tempvar value = (column6 - oods_values[144]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[144] * value;

    tempvar value = (column6 - oods_values[145]) / (point - pow37 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[145] * value;

    tempvar value = (column6 - oods_values[146]) / (point - pow38 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[146] * value;

    tempvar value = (column6 - oods_values[147]) / (point - pow41 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[147] * value;

    tempvar value = (column6 - oods_values[148]) / (point - pow44 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[148] * value;

    tempvar value = (column6 - oods_values[149]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[149] * value;

    tempvar value = (column6 - oods_values[150]) / (point - pow56 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[150] * value;

    tempvar value = (column6 - oods_values[151]) / (point - pow85 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[151] * value;

    tempvar value = (column6 - oods_values[152]) / (point - pow86 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[152] * value;

    tempvar value = (column6 - oods_values[153]) / (point - pow87 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[153] * value;

    tempvar value = (column6 - oods_values[154]) / (point - pow88 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[154] * value;

    tempvar value = (column6 - oods_values[155]) / (point - pow89 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[155] * value;

    tempvar value = (column6 - oods_values[156]) / (point - pow90 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[156] * value;

    tempvar value = (column6 - oods_values[157]) / (point - pow91 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[157] * value;

    tempvar value = (column6 - oods_values[158]) / (point - pow94 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[158] * value;

    tempvar value = (column6 - oods_values[159]) / (point - pow95 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[159] * value;

    tempvar value = (column6 - oods_values[160]) / (point - pow96 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[160] * value;

    tempvar value = (column6 - oods_values[161]) / (point - pow97 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[161] * value;

    tempvar value = (column6 - oods_values[162]) / (point - pow98 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[162] * value;

    tempvar value = (column6 - oods_values[163]) / (point - pow99 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[163] * value;

    tempvar value = (column6 - oods_values[164]) / (point - pow100 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[164] * value;

    tempvar value = (column6 - oods_values[165]) / (point - pow101 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[165] * value;

    tempvar value = (column7 - oods_values[166]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[166] * value;

    tempvar value = (column7 - oods_values[167]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[167] * value;

    tempvar value = (column8 - oods_values[168]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[168] * value;

    tempvar value = (column8 - oods_values[169]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[169] * value;

    tempvar value = (column9 - oods_values[170]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[170] * value;

    tempvar value = (column9 - oods_values[171]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[171] * value;

    tempvar value = (column9 - oods_values[172]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[172] * value;

    tempvar value = (column9 - oods_values[173]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[173] * value;

    // Sum the OODS boundary constraints on the composition polynomials.
    let (oods_point_to_deg) = pow(oods_point, CONSTRAINT_DEGREE);

    tempvar value = (column_values[10] - oods_values[174]) / (point - oods_point_to_deg);
    tempvar total_sum = total_sum + constraint_coefficients[174] * value;

    tempvar value = (column_values[11] - oods_values[175]) / (point - oods_point_to_deg);
    tempvar total_sum = total_sum + constraint_coefficients[175] * value;

    static_assert 176 == MASK_SIZE + CONSTRAINT_DEGREE;
    return (res=total_sum);
}
