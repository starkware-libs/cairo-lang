from starkware.cairo.stark_verifier.air.layouts.recursive_with_poseidon.global_values import (
    GlobalValues,
)
from starkware.cairo.common.math import safe_div, safe_mult
from starkware.cairo.common.pow import pow

const N_DYNAMIC_PARAMS = 0;
const N_CONSTRAINTS = 124;
const MASK_SIZE = 192;
const CPU_COMPONENT_STEP = 1;
const CPU_COMPONENT_HEIGHT = 16;
const PUBLIC_MEMORY_STEP = 16;
const HAS_DILUTED_POOL = 1;
const DILUTED_SPACING = 4;
const DILUTED_N_BITS = 16;
const PEDERSEN_BUILTIN_RATIO = 256;
const PEDERSEN_BUILTIN_ROW_RATIO = 4096;
const PEDERSEN_BUILTIN_REPETITIONS = 1;
const RANGE_CHECK_BUILTIN_RATIO = 16;
const RANGE_CHECK_BUILTIN_ROW_RATIO = 256;
const RANGE_CHECK_N_PARTS = 8;
const BITWISE__RATIO = 16;
const BITWISE__ROW_RATIO = 256;
const BITWISE__TOTAL_N_BITS = 251;
const POSEIDON__RATIO = 64;
const POSEIDON__ROW_RATIO = 1024;
const POSEIDON__M = 3;
const POSEIDON__ROUNDS_FULL = 8;
const POSEIDON__ROUNDS_PARTIAL = 83;
const HAS_OUTPUT_BUILTIN = 1;
const HAS_PEDERSEN_BUILTIN = 1;
const HAS_RANGE_CHECK_BUILTIN = 1;
const HAS_ECDSA_BUILTIN = 0;
const HAS_BITWISE_BUILTIN = 1;
const HAS_EC_OP_BUILTIN = 0;
const HAS_KECCAK_BUILTIN = 0;
const HAS_POSEIDON_BUILTIN = 1;
const HAS_RANGE_CHECK96_BUILTIN = 0;
const HAS_ADD_MOD_BUILTIN = 0;
const HAS_MUL_MOD_BUILTIN = 0;
const LAYOUT_CODE = 0x7265637572736976655f776974685f706f736569646f6e;
const CONSTRAINT_DEGREE = 2;
const LOG_CPU_COMPONENT_HEIGHT = 4;
const NUM_COLUMNS_FIRST = 6;
const NUM_COLUMNS_SECOND = 2;
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
    let (local pow0) = pow(point, (safe_div(global_values.trace_length, 4096)));
    local pow1 = pow0 * pow0;  // pow(point, (safe_div(global_values.trace_length, 2048))).
    local pow2 = pow1 * pow1;  // pow(point, (safe_div(global_values.trace_length, 1024))).
    local pow3 = pow2 * pow2;  // pow(point, (safe_div(global_values.trace_length, 512))).
    local pow4 = pow3 * pow3;  // pow(point, (safe_div(global_values.trace_length, 256))).
    local pow5 = pow4 * pow4;  // pow(point, (safe_div(global_values.trace_length, 128))).
    local pow6 = pow5 * pow5;  // pow(point, (safe_div(global_values.trace_length, 64))).
    local pow7 = pow6 * pow6;  // pow(point, (safe_div(global_values.trace_length, 32))).
    local pow8 = pow7 * pow7;  // pow(point, (safe_div(global_values.trace_length, 16))).
    local pow9 = pow8 * pow8;  // pow(point, (safe_div(global_values.trace_length, 8))).
    local pow10 = pow9 * pow9;  // pow(point, (safe_div(global_values.trace_length, 4))).
    local pow11 = pow10 * pow10;  // pow(point, (safe_div(global_values.trace_length, 2))).
    local pow12 = pow11 * pow11;  // pow(point, global_values.trace_length).
    let (local pow13) = pow(trace_generator, global_values.trace_length - 512);
    let (local pow14) = pow(trace_generator, global_values.trace_length - 256);
    let (local pow15) = pow(trace_generator, global_values.trace_length - 4096);
    let (local pow16) = pow(trace_generator, global_values.trace_length - 4);
    let (local pow17) = pow(trace_generator, global_values.trace_length - 2);
    let (local pow18) = pow(trace_generator, global_values.trace_length - 16);
    let (local pow19) = pow(trace_generator, (safe_div(global_values.trace_length, 2)));
    let (local pow20) = pow(
        trace_generator, (safe_div((safe_mult(255, global_values.trace_length)), 256))
    );
    let (local pow21) = pow(trace_generator, (safe_div(global_values.trace_length, 64)));
    local pow22 = pow21 * pow21;  // pow(trace_generator, (safe_div(global_values.trace_length, 32))).
    local pow23 = pow21 * pow22;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 64))).
    local pow24 = pow21 * pow23;  // pow(trace_generator, (safe_div(global_values.trace_length, 16))).
    local pow25 = pow21 * pow24;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 64))).
    local pow26 = pow21 * pow25;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 32))).
    local pow27 = pow19 * pow26;  // pow(trace_generator, (safe_div((safe_mult(19, global_values.trace_length)), 32))).
    local pow28 = pow21 * pow26;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 64))).
    local pow29 = pow21 * pow28;  // pow(trace_generator, (safe_div(global_values.trace_length, 8))).
    local pow30 = pow19 * pow29;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 8))).
    local pow31 = pow21 * pow29;  // pow(trace_generator, (safe_div((safe_mult(9, global_values.trace_length)), 64))).
    local pow32 = pow21 * pow31;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 32))).
    local pow33 = pow19 * pow32;  // pow(trace_generator, (safe_div((safe_mult(21, global_values.trace_length)), 32))).
    local pow34 = pow21 * pow32;  // pow(trace_generator, (safe_div((safe_mult(11, global_values.trace_length)), 64))).
    local pow35 = pow21 * pow34;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 16))).
    local pow36 = pow19 * pow35;  // pow(trace_generator, (safe_div((safe_mult(11, global_values.trace_length)), 16))).
    local pow37 = pow21 * pow35;  // pow(trace_generator, (safe_div((safe_mult(13, global_values.trace_length)), 64))).
    local pow38 = pow21 * pow37;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 32))).
    local pow39 = pow19 * pow38;  // pow(trace_generator, (safe_div((safe_mult(23, global_values.trace_length)), 32))).
    local pow40 = pow21 * pow38;  // pow(trace_generator, (safe_div((safe_mult(15, global_values.trace_length)), 64))).
    local pow41 = pow22 * pow39;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 4))).
    local pow42 = pow22 * pow41;  // pow(trace_generator, (safe_div((safe_mult(25, global_values.trace_length)), 32))).
    local pow43 = pow22 * pow42;  // pow(trace_generator, (safe_div((safe_mult(13, global_values.trace_length)), 16))).
    local pow44 = pow22 * pow43;  // pow(trace_generator, (safe_div((safe_mult(27, global_values.trace_length)), 32))).
    local pow45 = pow22 * pow44;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 8))).
    local pow46 = pow22 * pow45;  // pow(trace_generator, (safe_div((safe_mult(29, global_values.trace_length)), 32))).
    local pow47 = pow22 * pow46;  // pow(trace_generator, (safe_div((safe_mult(15, global_values.trace_length)), 16))).
    local pow48 = pow21 * pow47;  // pow(trace_generator, (safe_div((safe_mult(61, global_values.trace_length)), 64))).
    local pow49 = pow21 * pow48;  // pow(trace_generator, (safe_div((safe_mult(31, global_values.trace_length)), 32))).
    local pow50 = pow21 * pow49;  // pow(trace_generator, (safe_div((safe_mult(63, global_values.trace_length)), 64))).

    // Compute domains.
    tempvar domain0 = pow12 - 1;
    tempvar domain1 = pow11 - 1;
    tempvar domain2 = pow10 - 1;
    tempvar domain3 = pow9 - 1;
    tempvar domain4 = pow8 - pow47;
    tempvar domain5 = pow8 - 1;
    tempvar domain6 = pow7 - 1;
    tempvar domain7 = pow6 - 1;
    tempvar domain8 = pow5 - 1;
    tempvar domain9 = pow4 - 1;
    tempvar domain10 = pow4 - pow41;
    tempvar temp = pow4 - pow21;
    tempvar temp = temp * (pow4 - pow22);
    tempvar temp = temp * (pow4 - pow23);
    tempvar temp = temp * (pow4 - pow24);
    tempvar temp = temp * (pow4 - pow25);
    tempvar temp = temp * (pow4 - pow26);
    tempvar temp = temp * (pow4 - pow28);
    tempvar temp = temp * (pow4 - pow29);
    tempvar temp = temp * (pow4 - pow31);
    tempvar temp = temp * (pow4 - pow32);
    tempvar temp = temp * (pow4 - pow34);
    tempvar temp = temp * (pow4 - pow35);
    tempvar temp = temp * (pow4 - pow37);
    tempvar temp = temp * (pow4 - pow38);
    tempvar temp = temp * (pow4 - pow40);
    tempvar domain11 = temp * (domain9);
    tempvar domain12 = pow3 - 1;
    tempvar domain13 = pow3 - pow41;
    tempvar domain14 = pow2 - pow49;
    tempvar temp = pow2 - pow36;
    tempvar temp = temp * (pow2 - pow39);
    tempvar temp = temp * (pow2 - pow41);
    tempvar temp = temp * (pow2 - pow42);
    tempvar temp = temp * (pow2 - pow43);
    tempvar temp = temp * (pow2 - pow44);
    tempvar temp = temp * (pow2 - pow45);
    tempvar temp = temp * (pow2 - pow46);
    tempvar temp = temp * (pow2 - pow47);
    tempvar domain15 = temp * (domain14);
    tempvar domain16 = pow2 - 1;
    tempvar temp = pow2 - pow48;
    tempvar temp = temp * (pow2 - pow50);
    tempvar domain17 = temp * (domain14);
    tempvar temp = pow2 - pow27;
    tempvar temp = temp * (pow2 - pow30);
    tempvar temp = temp * (pow2 - pow33);
    tempvar domain18 = temp * (domain15);
    tempvar domain19 = pow1 - 1;
    tempvar domain20 = pow1 - pow20;
    tempvar domain21 = pow1 - pow50;
    tempvar domain22 = pow0 - pow19;
    tempvar domain23 = pow0 - 1;
    tempvar domain24 = point - pow18;
    tempvar domain25 = point - 1;
    tempvar domain26 = point - pow17;
    tempvar domain27 = point - pow16;
    tempvar domain28 = point - pow15;
    tempvar domain29 = point - pow14;
    tempvar domain30 = point - pow13;

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
    tempvar column1_row3 = mask_values[19];
    tempvar column1_row4 = mask_values[20];
    tempvar column1_row5 = mask_values[21];
    tempvar column1_row8 = mask_values[22];
    tempvar column1_row9 = mask_values[23];
    tempvar column1_row10 = mask_values[24];
    tempvar column1_row11 = mask_values[25];
    tempvar column1_row12 = mask_values[26];
    tempvar column1_row13 = mask_values[27];
    tempvar column1_row16 = mask_values[28];
    tempvar column1_row42 = mask_values[29];
    tempvar column1_row43 = mask_values[30];
    tempvar column1_row74 = mask_values[31];
    tempvar column1_row75 = mask_values[32];
    tempvar column1_row106 = mask_values[33];
    tempvar column1_row138 = mask_values[34];
    tempvar column1_row139 = mask_values[35];
    tempvar column1_row171 = mask_values[36];
    tempvar column1_row202 = mask_values[37];
    tempvar column1_row203 = mask_values[38];
    tempvar column1_row234 = mask_values[39];
    tempvar column1_row235 = mask_values[40];
    tempvar column1_row266 = mask_values[41];
    tempvar column1_row267 = mask_values[42];
    tempvar column1_row298 = mask_values[43];
    tempvar column1_row394 = mask_values[44];
    tempvar column1_row458 = mask_values[45];
    tempvar column1_row459 = mask_values[46];
    tempvar column1_row714 = mask_values[47];
    tempvar column1_row715 = mask_values[48];
    tempvar column1_row778 = mask_values[49];
    tempvar column1_row779 = mask_values[50];
    tempvar column1_row970 = mask_values[51];
    tempvar column1_row971 = mask_values[52];
    tempvar column1_row1034 = mask_values[53];
    tempvar column1_row1035 = mask_values[54];
    tempvar column1_row2058 = mask_values[55];
    tempvar column1_row2059 = mask_values[56];
    tempvar column1_row4106 = mask_values[57];
    tempvar column2_row0 = mask_values[58];
    tempvar column2_row1 = mask_values[59];
    tempvar column2_row2 = mask_values[60];
    tempvar column2_row3 = mask_values[61];
    tempvar column3_row0 = mask_values[62];
    tempvar column3_row1 = mask_values[63];
    tempvar column3_row2 = mask_values[64];
    tempvar column3_row3 = mask_values[65];
    tempvar column3_row4 = mask_values[66];
    tempvar column3_row8 = mask_values[67];
    tempvar column3_row12 = mask_values[68];
    tempvar column3_row16 = mask_values[69];
    tempvar column3_row20 = mask_values[70];
    tempvar column3_row24 = mask_values[71];
    tempvar column3_row28 = mask_values[72];
    tempvar column3_row32 = mask_values[73];
    tempvar column3_row36 = mask_values[74];
    tempvar column3_row40 = mask_values[75];
    tempvar column3_row44 = mask_values[76];
    tempvar column3_row48 = mask_values[77];
    tempvar column3_row52 = mask_values[78];
    tempvar column3_row56 = mask_values[79];
    tempvar column3_row60 = mask_values[80];
    tempvar column3_row64 = mask_values[81];
    tempvar column3_row66 = mask_values[82];
    tempvar column3_row128 = mask_values[83];
    tempvar column3_row130 = mask_values[84];
    tempvar column3_row176 = mask_values[85];
    tempvar column3_row180 = mask_values[86];
    tempvar column3_row184 = mask_values[87];
    tempvar column3_row188 = mask_values[88];
    tempvar column3_row192 = mask_values[89];
    tempvar column3_row194 = mask_values[90];
    tempvar column3_row240 = mask_values[91];
    tempvar column3_row244 = mask_values[92];
    tempvar column3_row248 = mask_values[93];
    tempvar column3_row252 = mask_values[94];
    tempvar column4_row0 = mask_values[95];
    tempvar column4_row1 = mask_values[96];
    tempvar column4_row2 = mask_values[97];
    tempvar column4_row3 = mask_values[98];
    tempvar column4_row4 = mask_values[99];
    tempvar column4_row5 = mask_values[100];
    tempvar column4_row6 = mask_values[101];
    tempvar column4_row7 = mask_values[102];
    tempvar column4_row8 = mask_values[103];
    tempvar column4_row9 = mask_values[104];
    tempvar column4_row11 = mask_values[105];
    tempvar column4_row12 = mask_values[106];
    tempvar column4_row13 = mask_values[107];
    tempvar column4_row44 = mask_values[108];
    tempvar column4_row76 = mask_values[109];
    tempvar column4_row108 = mask_values[110];
    tempvar column4_row140 = mask_values[111];
    tempvar column4_row172 = mask_values[112];
    tempvar column4_row204 = mask_values[113];
    tempvar column4_row236 = mask_values[114];
    tempvar column4_row1539 = mask_values[115];
    tempvar column4_row1547 = mask_values[116];
    tempvar column4_row1571 = mask_values[117];
    tempvar column4_row1579 = mask_values[118];
    tempvar column4_row2011 = mask_values[119];
    tempvar column4_row2019 = mask_values[120];
    tempvar column4_row2041 = mask_values[121];
    tempvar column4_row2045 = mask_values[122];
    tempvar column4_row2047 = mask_values[123];
    tempvar column4_row2049 = mask_values[124];
    tempvar column4_row2051 = mask_values[125];
    tempvar column4_row2053 = mask_values[126];
    tempvar column4_row4089 = mask_values[127];
    tempvar column5_row0 = mask_values[128];
    tempvar column5_row1 = mask_values[129];
    tempvar column5_row2 = mask_values[130];
    tempvar column5_row4 = mask_values[131];
    tempvar column5_row6 = mask_values[132];
    tempvar column5_row8 = mask_values[133];
    tempvar column5_row9 = mask_values[134];
    tempvar column5_row10 = mask_values[135];
    tempvar column5_row12 = mask_values[136];
    tempvar column5_row14 = mask_values[137];
    tempvar column5_row16 = mask_values[138];
    tempvar column5_row17 = mask_values[139];
    tempvar column5_row22 = mask_values[140];
    tempvar column5_row24 = mask_values[141];
    tempvar column5_row25 = mask_values[142];
    tempvar column5_row30 = mask_values[143];
    tempvar column5_row33 = mask_values[144];
    tempvar column5_row38 = mask_values[145];
    tempvar column5_row41 = mask_values[146];
    tempvar column5_row46 = mask_values[147];
    tempvar column5_row49 = mask_values[148];
    tempvar column5_row54 = mask_values[149];
    tempvar column5_row57 = mask_values[150];
    tempvar column5_row65 = mask_values[151];
    tempvar column5_row73 = mask_values[152];
    tempvar column5_row81 = mask_values[153];
    tempvar column5_row89 = mask_values[154];
    tempvar column5_row97 = mask_values[155];
    tempvar column5_row105 = mask_values[156];
    tempvar column5_row137 = mask_values[157];
    tempvar column5_row169 = mask_values[158];
    tempvar column5_row201 = mask_values[159];
    tempvar column5_row393 = mask_values[160];
    tempvar column5_row409 = mask_values[161];
    tempvar column5_row425 = mask_values[162];
    tempvar column5_row457 = mask_values[163];
    tempvar column5_row473 = mask_values[164];
    tempvar column5_row489 = mask_values[165];
    tempvar column5_row521 = mask_values[166];
    tempvar column5_row553 = mask_values[167];
    tempvar column5_row585 = mask_values[168];
    tempvar column5_row609 = mask_values[169];
    tempvar column5_row625 = mask_values[170];
    tempvar column5_row641 = mask_values[171];
    tempvar column5_row657 = mask_values[172];
    tempvar column5_row673 = mask_values[173];
    tempvar column5_row689 = mask_values[174];
    tempvar column5_row905 = mask_values[175];
    tempvar column5_row921 = mask_values[176];
    tempvar column5_row937 = mask_values[177];
    tempvar column5_row969 = mask_values[178];
    tempvar column5_row982 = mask_values[179];
    tempvar column5_row985 = mask_values[180];
    tempvar column5_row998 = mask_values[181];
    tempvar column5_row1001 = mask_values[182];
    tempvar column5_row1014 = mask_values[183];
    tempvar column6_inter1_row0 = mask_values[184];
    tempvar column6_inter1_row1 = mask_values[185];
    tempvar column6_inter1_row2 = mask_values[186];
    tempvar column6_inter1_row3 = mask_values[187];
    tempvar column7_inter1_row0 = mask_values[188];
    tempvar column7_inter1_row1 = mask_values[189];
    tempvar column7_inter1_row2 = mask_values[190];
    tempvar column7_inter1_row5 = mask_values[191];

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
    tempvar npc_reg_0 = column1_row0 + cpu__decode__opcode_range_check__bit_2 + 1;
    tempvar cpu__decode__opcode_range_check__bit_10 = column0_row10 - (
        column0_row11 + column0_row11
    );
    tempvar cpu__decode__opcode_range_check__bit_11 = column0_row11 - (
        column0_row12 + column0_row12
    );
    tempvar cpu__decode__opcode_range_check__bit_14 = column0_row14 - (
        column0_row15 + column0_row15
    );
    tempvar memory__address_diff_0 = column2_row2 - column2_row0;
    tempvar range_check16__diff_0 = column4_row6 - column4_row2;
    tempvar pedersen__hash0__ec_subset_sum__bit_0 = column4_row3 - (column4_row11 + column4_row11);
    tempvar pedersen__hash0__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash0__ec_subset_sum__bit_0;
    tempvar range_check_builtin__value0_0 = column4_row12;
    tempvar range_check_builtin__value1_0 = range_check_builtin__value0_0 *
        global_values.offset_size + column4_row44;
    tempvar range_check_builtin__value2_0 = range_check_builtin__value1_0 *
        global_values.offset_size + column4_row76;
    tempvar range_check_builtin__value3_0 = range_check_builtin__value2_0 *
        global_values.offset_size + column4_row108;
    tempvar range_check_builtin__value4_0 = range_check_builtin__value3_0 *
        global_values.offset_size + column4_row140;
    tempvar range_check_builtin__value5_0 = range_check_builtin__value4_0 *
        global_values.offset_size + column4_row172;
    tempvar range_check_builtin__value6_0 = range_check_builtin__value5_0 *
        global_values.offset_size + column4_row204;
    tempvar range_check_builtin__value7_0 = range_check_builtin__value6_0 *
        global_values.offset_size + column4_row236;
    tempvar bitwise__sum_var_0_0 = column3_row0 + column3_row4 * 2 + column3_row8 * 4 +
        column3_row12 * 8 + column3_row16 * 18446744073709551616 + column3_row20 *
        36893488147419103232 + column3_row24 * 73786976294838206464 + column3_row28 *
        147573952589676412928;
    tempvar bitwise__sum_var_8_0 = column3_row32 * 340282366920938463463374607431768211456 +
        column3_row36 * 680564733841876926926749214863536422912 + column3_row40 *
        1361129467683753853853498429727072845824 + column3_row44 *
        2722258935367507707706996859454145691648 + column3_row48 *
        6277101735386680763835789423207666416102355444464034512896 + column3_row52 *
        12554203470773361527671578846415332832204710888928069025792 + column3_row56 *
        25108406941546723055343157692830665664409421777856138051584 + column3_row60 *
        50216813883093446110686315385661331328818843555712276103168;
    tempvar poseidon__poseidon__full_rounds_state0_cubed_0 = column5_row9 * column5_row105;
    tempvar poseidon__poseidon__full_rounds_state1_cubed_0 = column5_row73 * column5_row25;
    tempvar poseidon__poseidon__full_rounds_state2_cubed_0 = column5_row41 * column5_row89;
    tempvar poseidon__poseidon__full_rounds_state0_cubed_7 = column5_row905 * column5_row1001;
    tempvar poseidon__poseidon__full_rounds_state1_cubed_7 = column5_row969 * column5_row921;
    tempvar poseidon__poseidon__full_rounds_state2_cubed_7 = column5_row937 * column5_row985;
    tempvar poseidon__poseidon__full_rounds_state0_cubed_3 = column5_row393 * column5_row489;
    tempvar poseidon__poseidon__full_rounds_state1_cubed_3 = column5_row457 * column5_row409;
    tempvar poseidon__poseidon__full_rounds_state2_cubed_3 = column5_row425 * column5_row473;
    tempvar poseidon__poseidon__partial_rounds_state0_cubed_0 = column5_row6 * column5_row14;
    tempvar poseidon__poseidon__partial_rounds_state0_cubed_1 = column5_row22 * column5_row30;
    tempvar poseidon__poseidon__partial_rounds_state0_cubed_2 = column5_row38 * column5_row46;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_0 = column5_row1 * column5_row17;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_1 = column5_row33 * column5_row49;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_2 = column5_row65 * column5_row81;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_19 = column5_row609 * column5_row625;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_20 = column5_row641 * column5_row657;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_21 = column5_row673 * column5_row689;

    // Sum constraints.
    tempvar total_sum = 0;

    // Constraint: cpu/decode/opcode_range_check/bit.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_0 * cpu__decode__opcode_range_check__bit_0 -
        cpu__decode__opcode_range_check__bit_0
    ) * domain4 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[0] * value;

    // Constraint: cpu/decode/opcode_range_check/zero.
    tempvar value = (column0_row0) / domain4;
    tempvar total_sum = total_sum + constraint_coefficients[1] * value;

    // Constraint: cpu/decode/opcode_range_check_input.
    tempvar value = (
        column1_row1 -
        (
            (
                (column0_row0 * global_values.offset_size + column4_row4) *
                global_values.offset_size +
                column4_row8
            ) * global_values.offset_size +
            column4_row0
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
        column1_row8 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_0 * column5_row8 +
            (1 - cpu__decode__opcode_range_check__bit_0) * column5_row0 +
            column4_row0
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    // Constraint: cpu/operands/mem0_addr.
    tempvar value = (
        column1_row4 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_1 * column5_row8 +
            (1 - cpu__decode__opcode_range_check__bit_1) * column5_row0 +
            column4_row8
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    // Constraint: cpu/operands/mem1_addr.
    tempvar value = (
        column1_row12 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_2 * column1_row0 +
            cpu__decode__opcode_range_check__bit_4 * column5_row0 +
            cpu__decode__opcode_range_check__bit_3 * column5_row8 +
            cpu__decode__flag_op1_base_op0_0 * column1_row5 +
            column4_row4
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    // Constraint: cpu/operands/ops_mul.
    tempvar value = (column5_row4 - column1_row5 * column1_row13) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    // Constraint: cpu/operands/res.
    tempvar value = (
        (1 - cpu__decode__opcode_range_check__bit_9) * column5_row12 -
        (
            cpu__decode__opcode_range_check__bit_5 * (column1_row5 + column1_row13) +
            cpu__decode__opcode_range_check__bit_6 * column5_row4 +
            cpu__decode__flag_res_op1_0 * column1_row13
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    // Constraint: cpu/update_registers/update_pc/tmp0.
    tempvar value = (column5_row2 - cpu__decode__opcode_range_check__bit_9 * column1_row9) *
        domain24 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    // Constraint: cpu/update_registers/update_pc/tmp1.
    tempvar value = (column5_row10 - column5_row2 * column5_row12) * domain24 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_negative.
    tempvar value = (
        (1 - cpu__decode__opcode_range_check__bit_9) * column1_row16 +
        column5_row2 * (column1_row16 - (column1_row0 + column1_row13)) -
        (
            cpu__decode__flag_pc_update_regular_0 * npc_reg_0 +
            cpu__decode__opcode_range_check__bit_7 * column5_row12 +
            cpu__decode__opcode_range_check__bit_8 * (column1_row0 + column5_row12)
        )
    ) * domain24 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_positive.
    tempvar value = (
        (column5_row10 - cpu__decode__opcode_range_check__bit_9) * (column1_row16 - npc_reg_0)
    ) * domain24 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    // Constraint: cpu/update_registers/update_ap/ap_update.
    tempvar value = (
        column5_row16 -
        (
            column5_row0 +
            cpu__decode__opcode_range_check__bit_10 * column5_row12 +
            cpu__decode__opcode_range_check__bit_11 +
            cpu__decode__opcode_range_check__bit_12 * 2
        )
    ) * domain24 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    // Constraint: cpu/update_registers/update_fp/fp_update.
    tempvar value = (
        column5_row24 -
        (
            cpu__decode__fp_update_regular_0 * column5_row8 +
            cpu__decode__opcode_range_check__bit_13 * column1_row9 +
            cpu__decode__opcode_range_check__bit_12 * (column5_row0 + 2)
        )
    ) * domain24 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    // Constraint: cpu/opcodes/call/push_fp.
    tempvar value = (cpu__decode__opcode_range_check__bit_12 * (column1_row9 - column5_row8)) /
        domain5;
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    // Constraint: cpu/opcodes/call/push_pc.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (
            column1_row5 - (column1_row0 + cpu__decode__opcode_range_check__bit_2 + 1)
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    // Constraint: cpu/opcodes/call/off0.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (column4_row0 - global_values.half_offset_size)
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    // Constraint: cpu/opcodes/call/off1.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (
            column4_row8 - (global_values.half_offset_size + 1)
        )
    ) / domain5;
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
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    // Constraint: cpu/opcodes/ret/off0.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_13 * (
            column4_row0 + 2 - global_values.half_offset_size
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    // Constraint: cpu/opcodes/ret/off2.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_13 * (
            column4_row4 + 1 - global_values.half_offset_size
        )
    ) / domain5;
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
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    // Constraint: cpu/opcodes/assert_eq/assert_eq.
    tempvar value = (cpu__decode__opcode_range_check__bit_14 * (column1_row9 - column5_row12)) /
        domain5;
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    // Constraint: initial_ap.
    tempvar value = (column5_row0 - global_values.initial_ap) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    // Constraint: initial_fp.
    tempvar value = (column5_row8 - global_values.initial_ap) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    // Constraint: initial_pc.
    tempvar value = (column1_row0 - global_values.initial_pc) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    // Constraint: final_ap.
    tempvar value = (column5_row0 - global_values.final_ap) / domain24;
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    // Constraint: final_fp.
    tempvar value = (column5_row8 - global_values.initial_ap) / domain24;
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    // Constraint: final_pc.
    tempvar value = (column1_row0 - global_values.final_pc) / domain24;
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    // Constraint: memory/multi_column_perm/perm/init0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column2_row0 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column2_row1
            )
        ) * column6_inter1_row0 +
        column1_row0 +
        global_values.memory__multi_column_perm__hash_interaction_elm0 * column1_row1 -
        global_values.memory__multi_column_perm__perm__interaction_elm
    ) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    // Constraint: memory/multi_column_perm/perm/step0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column2_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column2_row3
            )
        ) * column6_inter1_row2 -
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column1_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column1_row3
            )
        ) * column6_inter1_row0
    ) * domain26 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    // Constraint: memory/multi_column_perm/perm/last.
    tempvar value = (
        column6_inter1_row0 - global_values.memory__multi_column_perm__perm__public_memory_prod
    ) / domain26;
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    // Constraint: memory/diff_is_bit.
    tempvar value = (memory__address_diff_0 * memory__address_diff_0 - memory__address_diff_0) *
        domain26 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    // Constraint: memory/is_func.
    tempvar value = ((memory__address_diff_0 - 1) * (column2_row1 - column2_row3)) * domain26 /
        domain1;
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    // Constraint: memory/initial_addr.
    tempvar value = (column2_row0 - 1) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    // Constraint: public_memory_addr_zero.
    tempvar value = (column1_row2) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    // Constraint: public_memory_value_zero.
    tempvar value = (column1_row3) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    // Constraint: range_check16/perm/init0.
    tempvar value = (
        (global_values.range_check16__perm__interaction_elm - column4_row2) * column7_inter1_row1 +
        column4_row0 -
        global_values.range_check16__perm__interaction_elm
    ) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    // Constraint: range_check16/perm/step0.
    tempvar value = (
        (global_values.range_check16__perm__interaction_elm - column4_row6) * column7_inter1_row5 -
        (global_values.range_check16__perm__interaction_elm - column4_row4) * column7_inter1_row1
    ) * domain27 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    // Constraint: range_check16/perm/last.
    tempvar value = (column7_inter1_row1 - global_values.range_check16__perm__public_memory_prod) /
        domain27;
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    // Constraint: range_check16/diff_is_bit.
    tempvar value = (range_check16__diff_0 * range_check16__diff_0 - range_check16__diff_0) *
        domain27 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    // Constraint: range_check16/minimum.
    tempvar value = (column4_row2 - global_values.range_check_min) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    // Constraint: range_check16/maximum.
    tempvar value = (column4_row2 - global_values.range_check_max) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    // Constraint: diluted_check/permutation/init0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column3_row1) *
        column7_inter1_row0 +
        column3_row0 -
        global_values.diluted_check__permutation__interaction_elm
    ) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    // Constraint: diluted_check/permutation/step0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column3_row3) *
        column7_inter1_row2 -
        (global_values.diluted_check__permutation__interaction_elm - column3_row2) *
        column7_inter1_row0
    ) * domain26 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    // Constraint: diluted_check/permutation/last.
    tempvar value = (
        column7_inter1_row0 - global_values.diluted_check__permutation__public_memory_prod
    ) / domain26;
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    // Constraint: diluted_check/init.
    tempvar value = (column6_inter1_row1 - 1) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    // Constraint: diluted_check/first_element.
    tempvar value = (column3_row1 - global_values.diluted_check__first_elm) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    // Constraint: diluted_check/step.
    tempvar value = (
        column6_inter1_row3 -
        (
            column6_inter1_row1 * (
                1 + global_values.diluted_check__interaction_z * (column3_row3 - column3_row1)
            ) +
            global_values.diluted_check__interaction_alpha * (column3_row3 - column3_row1) * (
                column3_row3 - column3_row1
            )
        )
    ) * domain26 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    // Constraint: diluted_check/last.
    tempvar value = (column6_inter1_row1 - global_values.diluted_check__final_cum_val) / domain26;
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column5_row57 * (column4_row3 - (column4_row11 + column4_row11))) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column5_row57 * (
            column4_row11 -
            3138550867693340381917894711603833208051177722232017256448 * column4_row1539
        )
    ) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column5_row57 - column4_row2047 * (column4_row1539 - (column4_row1547 + column4_row1547))
    ) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column4_row2047 * (column4_row1547 - 8 * column4_row1571)) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column4_row2047 -
        (column4_row2011 - (column4_row2019 + column4_row2019)) * (
            column4_row1571 - (column4_row1579 + column4_row1579)
        )
    ) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column4_row2011 - (column4_row2019 + column4_row2019)) * (
            column4_row1579 - 18014398509481984 * column4_row2011
        )
    ) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (pedersen__hash0__ec_subset_sum__bit_0 - 1)
    ) * domain20 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_extraction_end.
    tempvar value = (column4_row3) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/zeros_tail.
    tempvar value = (column4_row3) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column4_row5 - global_values.pedersen__points__y) -
        column4_row7 * (column4_row1 - global_values.pedersen__points__x)
    ) * domain20 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/x.
    tempvar value = (
        column4_row7 * column4_row7 -
        pedersen__hash0__ec_subset_sum__bit_0 * (
            column4_row1 + global_values.pedersen__points__x + column4_row9
        )
    ) * domain20 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column4_row5 + column4_row13) -
        column4_row7 * (column4_row1 - column4_row9)
    ) * domain20 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column4_row9 - column4_row1)) *
        domain20 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column4_row13 - column4_row5)) *
        domain20 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    // Constraint: pedersen/hash0/copy_point/x.
    tempvar value = (column4_row2049 - column4_row2041) * domain22 / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    // Constraint: pedersen/hash0/copy_point/y.
    tempvar value = (column4_row2053 - column4_row2045) * domain22 / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    // Constraint: pedersen/hash0/init/x.
    tempvar value = (column4_row1 - global_values.pedersen__shift_point.x) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    // Constraint: pedersen/hash0/init/y.
    tempvar value = (column4_row5 - global_values.pedersen__shift_point.y) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    // Constraint: pedersen/input0_value0.
    tempvar value = (column1_row11 - column4_row3) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    // Constraint: pedersen/input0_addr.
    tempvar value = (column1_row4106 - (column1_row1034 + 1)) * domain28 / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    // Constraint: pedersen/init_addr.
    tempvar value = (column1_row10 - global_values.initial_pedersen_addr) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    // Constraint: pedersen/input1_value0.
    tempvar value = (column1_row2059 - column4_row2051) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    // Constraint: pedersen/input1_addr.
    tempvar value = (column1_row2058 - (column1_row10 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    // Constraint: pedersen/output_value0.
    tempvar value = (column1_row1035 - column4_row4089) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    // Constraint: pedersen/output_addr.
    tempvar value = (column1_row1034 - (column1_row2058 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    // Constraint: range_check_builtin/value.
    tempvar value = (range_check_builtin__value7_0 - column1_row139) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    // Constraint: range_check_builtin/addr_step.
    tempvar value = (column1_row394 - (column1_row138 + 1)) * domain29 / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    // Constraint: range_check_builtin/init_addr.
    tempvar value = (column1_row138 - global_values.initial_range_check_addr) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    // Constraint: bitwise/init_var_pool_addr.
    tempvar value = (column1_row42 - global_values.initial_bitwise_addr) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    // Constraint: bitwise/step_var_pool_addr.
    tempvar value = (column1_row106 - (column1_row42 + 1)) * domain10 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    // Constraint: bitwise/x_or_y_addr.
    tempvar value = (column1_row74 - (column1_row234 + 1)) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    // Constraint: bitwise/next_var_pool_addr.
    tempvar value = (column1_row298 - (column1_row74 + 1)) * domain29 / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    // Constraint: bitwise/partition.
    tempvar value = (bitwise__sum_var_0_0 + bitwise__sum_var_8_0 - column1_row43) / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    // Constraint: bitwise/or_is_and_plus_xor.
    tempvar value = (column1_row75 - (column1_row171 + column1_row235)) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    // Constraint: bitwise/addition_is_xor_with_and.
    tempvar value = (
        column3_row0 + column3_row64 - (column3_row192 + column3_row128 + column3_row128)
    ) / domain11;
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    // Constraint: bitwise/unique_unpacking192.
    tempvar value = ((column3_row176 + column3_row240) * 16 - column3_row2) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    // Constraint: bitwise/unique_unpacking193.
    tempvar value = ((column3_row180 + column3_row244) * 16 - column3_row130) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    // Constraint: bitwise/unique_unpacking194.
    tempvar value = ((column3_row184 + column3_row248) * 16 - column3_row66) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    // Constraint: bitwise/unique_unpacking195.
    tempvar value = ((column3_row188 + column3_row252) * 256 - column3_row194) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    // Constraint: poseidon/param_0/init_input_output_addr.
    tempvar value = (column1_row266 - global_values.initial_poseidon_addr) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    // Constraint: poseidon/param_0/addr_input_output_step.
    tempvar value = (column1_row778 - (column1_row266 + 3)) * domain30 / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    // Constraint: poseidon/param_1/init_input_output_addr.
    tempvar value = (column1_row202 - (global_values.initial_poseidon_addr + 1)) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    // Constraint: poseidon/param_1/addr_input_output_step.
    tempvar value = (column1_row714 - (column1_row202 + 3)) * domain30 / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    // Constraint: poseidon/param_2/init_input_output_addr.
    tempvar value = (column1_row458 - (global_values.initial_poseidon_addr + 2)) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    // Constraint: poseidon/param_2/addr_input_output_step.
    tempvar value = (column1_row970 - (column1_row458 + 3)) * domain30 / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    // Constraint: poseidon/poseidon/full_rounds_state0_squaring.
    tempvar value = (column5_row9 * column5_row9 - column5_row105) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    // Constraint: poseidon/poseidon/full_rounds_state1_squaring.
    tempvar value = (column5_row73 * column5_row73 - column5_row25) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    // Constraint: poseidon/poseidon/full_rounds_state2_squaring.
    tempvar value = (column5_row41 * column5_row41 - column5_row89) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    // Constraint: poseidon/poseidon/partial_rounds_state0_squaring.
    tempvar value = (column5_row6 * column5_row6 - column5_row14) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    // Constraint: poseidon/poseidon/partial_rounds_state1_squaring.
    tempvar value = (column5_row1 * column5_row1 - column5_row17) * domain15 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    // Constraint: poseidon/poseidon/add_first_round_key0.
    tempvar value = (
        column1_row267 +
        2950795762459345168613727575620414179244544320470208355568817838579231751791 -
        column5_row9
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    // Constraint: poseidon/poseidon/add_first_round_key1.
    tempvar value = (
        column1_row203 +
        1587446564224215276866294500450702039420286416111469274423465069420553242820 -
        column5_row73
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    // Constraint: poseidon/poseidon/add_first_round_key2.
    tempvar value = (
        column1_row459 +
        1645965921169490687904413452218868659025437693527479459426157555728339600137 -
        column5_row41
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    // Constraint: poseidon/poseidon/full_round0.
    tempvar value = (
        column5_row137 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state1_cubed_0 +
            poseidon__poseidon__full_rounds_state2_cubed_0 +
            global_values.poseidon__poseidon__full_round_key0
        )
    ) * domain13 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    // Constraint: poseidon/poseidon/full_round1.
    tempvar value = (
        column5_row201 +
        poseidon__poseidon__full_rounds_state1_cubed_0 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state2_cubed_0 +
            global_values.poseidon__poseidon__full_round_key1
        )
    ) * domain13 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    // Constraint: poseidon/poseidon/full_round2.
    tempvar value = (
        column5_row169 +
        poseidon__poseidon__full_rounds_state2_cubed_0 +
        poseidon__poseidon__full_rounds_state2_cubed_0 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state1_cubed_0 +
            global_values.poseidon__poseidon__full_round_key2
        )
    ) * domain13 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    // Constraint: poseidon/poseidon/last_full_round0.
    tempvar value = (
        column1_row779 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state1_cubed_7 +
            poseidon__poseidon__full_rounds_state2_cubed_7
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    // Constraint: poseidon/poseidon/last_full_round1.
    tempvar value = (
        column1_row715 +
        poseidon__poseidon__full_rounds_state1_cubed_7 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state2_cubed_7
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    // Constraint: poseidon/poseidon/last_full_round2.
    tempvar value = (
        column1_row971 +
        poseidon__poseidon__full_rounds_state2_cubed_7 +
        poseidon__poseidon__full_rounds_state2_cubed_7 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state1_cubed_7
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    // Constraint: poseidon/poseidon/copy_partial_rounds0_i0.
    tempvar value = (column5_row982 - column5_row1) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    // Constraint: poseidon/poseidon/copy_partial_rounds0_i1.
    tempvar value = (column5_row998 - column5_row33) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    // Constraint: poseidon/poseidon/copy_partial_rounds0_i2.
    tempvar value = (column5_row1014 - column5_row65) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    // Constraint: poseidon/poseidon/margin_full_to_partial0.
    tempvar value = (
        column5_row6 +
        poseidon__poseidon__full_rounds_state2_cubed_3 +
        poseidon__poseidon__full_rounds_state2_cubed_3 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_3 +
            poseidon__poseidon__full_rounds_state1_cubed_3 +
            2121140748740143694053732746913428481442990369183417228688865837805149503386
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    // Constraint: poseidon/poseidon/margin_full_to_partial1.
    tempvar value = (
        column5_row22 -
        (
            3618502788666131213697322783095070105623107215331596699973092056135872020477 *
            poseidon__poseidon__full_rounds_state1_cubed_3 +
            10 * poseidon__poseidon__full_rounds_state2_cubed_3 +
            4 * column5_row6 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state0_cubed_0 +
            2006642341318481906727563724340978325665491359415674592697055778067937914672
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    // Constraint: poseidon/poseidon/margin_full_to_partial2.
    tempvar value = (
        column5_row38 -
        (
            8 * poseidon__poseidon__full_rounds_state2_cubed_3 +
            4 * column5_row6 +
            6 * poseidon__poseidon__partial_rounds_state0_cubed_0 +
            column5_row22 +
            column5_row22 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state0_cubed_1 +
            427751140904099001132521606468025610873158555767197326325930641757709538586
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    // Constraint: poseidon/poseidon/partial_round0.
    tempvar value = (
        column5_row54 -
        (
            8 * poseidon__poseidon__partial_rounds_state0_cubed_0 +
            4 * column5_row22 +
            6 * poseidon__poseidon__partial_rounds_state0_cubed_1 +
            column5_row38 +
            column5_row38 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state0_cubed_2 +
            global_values.poseidon__poseidon__partial_round_key0
        )
    ) * domain17 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    // Constraint: poseidon/poseidon/partial_round1.
    tempvar value = (
        column5_row97 -
        (
            8 * poseidon__poseidon__partial_rounds_state1_cubed_0 +
            4 * column5_row33 +
            6 * poseidon__poseidon__partial_rounds_state1_cubed_1 +
            column5_row65 +
            column5_row65 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state1_cubed_2 +
            global_values.poseidon__poseidon__partial_round_key1
        )
    ) * domain18 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    // Constraint: poseidon/poseidon/margin_partial_to_full0.
    tempvar value = (
        column5_row521 -
        (
            16 * poseidon__poseidon__partial_rounds_state1_cubed_19 +
            8 * column5_row641 +
            16 * poseidon__poseidon__partial_rounds_state1_cubed_20 +
            6 * column5_row673 +
            poseidon__poseidon__partial_rounds_state1_cubed_21 +
            560279373700919169769089400651532183647886248799764942664266404650165812023
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    // Constraint: poseidon/poseidon/margin_partial_to_full1.
    tempvar value = (
        column5_row585 -
        (
            4 * poseidon__poseidon__partial_rounds_state1_cubed_20 +
            column5_row673 +
            column5_row673 +
            poseidon__poseidon__partial_rounds_state1_cubed_21 +
            1401754474293352309994371631695783042590401941592571735921592823982231996415
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    // Constraint: poseidon/poseidon/margin_partial_to_full2.
    tempvar value = (
        column5_row553 -
        (
            8 * poseidon__poseidon__partial_rounds_state1_cubed_19 +
            4 * column5_row641 +
            6 * poseidon__poseidon__partial_rounds_state1_cubed_20 +
            column5_row673 +
            column5_row673 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state1_cubed_21 +
            1246177936547655338400308396717835700699368047388302793172818304164989556526
        )
    ) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

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
    let (local pow1) = pow(trace_generator, 4089);
    let (local pow2) = pow(trace_generator, 2011);
    let (local pow3) = pow(trace_generator, 1539);
    let (local pow4) = pow(trace_generator, 1);
    local pow5 = pow4 * pow4;  // pow(trace_generator, 2).
    local pow6 = pow4 * pow5;  // pow(trace_generator, 3).
    local pow7 = pow4 * pow6;  // pow(trace_generator, 4).
    local pow8 = pow4 * pow7;  // pow(trace_generator, 5).
    local pow9 = pow4 * pow8;  // pow(trace_generator, 6).
    local pow10 = pow4 * pow9;  // pow(trace_generator, 7).
    local pow11 = pow4 * pow10;  // pow(trace_generator, 8).
    local pow12 = pow3 * pow11;  // pow(trace_generator, 1547).
    local pow13 = pow4 * pow11;  // pow(trace_generator, 9).
    local pow14 = pow4 * pow13;  // pow(trace_generator, 10).
    local pow15 = pow4 * pow14;  // pow(trace_generator, 11).
    local pow16 = pow4 * pow15;  // pow(trace_generator, 12).
    local pow17 = pow4 * pow16;  // pow(trace_generator, 13).
    local pow18 = pow4 * pow17;  // pow(trace_generator, 14).
    local pow19 = pow4 * pow18;  // pow(trace_generator, 15).
    local pow20 = pow4 * pow19;  // pow(trace_generator, 16).
    local pow21 = pow4 * pow20;  // pow(trace_generator, 17).
    local pow22 = pow6 * pow21;  // pow(trace_generator, 20).
    local pow23 = pow5 * pow22;  // pow(trace_generator, 22).
    local pow24 = pow5 * pow23;  // pow(trace_generator, 24).
    local pow25 = pow4 * pow24;  // pow(trace_generator, 25).
    local pow26 = pow6 * pow25;  // pow(trace_generator, 28).
    local pow27 = pow5 * pow26;  // pow(trace_generator, 30).
    local pow28 = pow5 * pow27;  // pow(trace_generator, 32).
    local pow29 = pow4 * pow28;  // pow(trace_generator, 33).
    local pow30 = pow3 * pow28;  // pow(trace_generator, 1571).
    local pow31 = pow6 * pow29;  // pow(trace_generator, 36).
    local pow32 = pow5 * pow31;  // pow(trace_generator, 38).
    local pow33 = pow5 * pow32;  // pow(trace_generator, 40).
    local pow34 = pow4 * pow33;  // pow(trace_generator, 41).
    local pow35 = pow4 * pow34;  // pow(trace_generator, 42).
    local pow36 = pow4 * pow35;  // pow(trace_generator, 43).
    local pow37 = pow4 * pow36;  // pow(trace_generator, 44).
    local pow38 = pow5 * pow37;  // pow(trace_generator, 46).
    local pow39 = pow5 * pow38;  // pow(trace_generator, 48).
    local pow40 = pow4 * pow39;  // pow(trace_generator, 49).
    local pow41 = pow6 * pow40;  // pow(trace_generator, 52).
    local pow42 = pow5 * pow41;  // pow(trace_generator, 54).
    local pow43 = pow5 * pow42;  // pow(trace_generator, 56).
    local pow44 = pow4 * pow43;  // pow(trace_generator, 57).
    local pow45 = pow6 * pow44;  // pow(trace_generator, 60).
    local pow46 = pow7 * pow45;  // pow(trace_generator, 64).
    local pow47 = pow4 * pow46;  // pow(trace_generator, 65).
    local pow48 = pow4 * pow47;  // pow(trace_generator, 66).
    local pow49 = pow10 * pow48;  // pow(trace_generator, 73).
    local pow50 = pow4 * pow49;  // pow(trace_generator, 74).
    local pow51 = pow4 * pow50;  // pow(trace_generator, 75).
    local pow52 = pow4 * pow51;  // pow(trace_generator, 76).
    local pow53 = pow8 * pow52;  // pow(trace_generator, 81).
    local pow54 = pow11 * pow53;  // pow(trace_generator, 89).
    local pow55 = pow11 * pow54;  // pow(trace_generator, 97).
    local pow56 = pow11 * pow55;  // pow(trace_generator, 105).
    local pow57 = pow4 * pow56;  // pow(trace_generator, 106).
    local pow58 = pow5 * pow57;  // pow(trace_generator, 108).
    local pow59 = pow22 * pow58;  // pow(trace_generator, 128).
    local pow60 = pow5 * pow59;  // pow(trace_generator, 130).
    local pow61 = pow10 * pow60;  // pow(trace_generator, 137).
    local pow62 = pow4 * pow61;  // pow(trace_generator, 138).
    local pow63 = pow4 * pow62;  // pow(trace_generator, 139).
    local pow64 = pow27 * pow63;  // pow(trace_generator, 169).
    local pow65 = pow5 * pow64;  // pow(trace_generator, 171).
    local pow66 = pow4 * pow63;  // pow(trace_generator, 140).
    local pow67 = pow4 * pow65;  // pow(trace_generator, 172).
    local pow68 = pow7 * pow67;  // pow(trace_generator, 176).
    local pow69 = pow7 * pow68;  // pow(trace_generator, 180).
    local pow70 = pow7 * pow69;  // pow(trace_generator, 184).
    local pow71 = pow7 * pow70;  // pow(trace_generator, 188).
    local pow72 = pow7 * pow71;  // pow(trace_generator, 192).
    local pow73 = pow5 * pow72;  // pow(trace_generator, 194).
    local pow74 = pow10 * pow73;  // pow(trace_generator, 201).
    local pow75 = pow4 * pow74;  // pow(trace_generator, 202).
    local pow76 = pow4 * pow75;  // pow(trace_generator, 203).
    local pow77 = pow72 * pow74;  // pow(trace_generator, 393).
    local pow78 = pow4 * pow76;  // pow(trace_generator, 204).
    local pow79 = pow27 * pow78;  // pow(trace_generator, 234).
    local pow80 = pow4 * pow79;  // pow(trace_generator, 235).
    local pow81 = pow4 * pow80;  // pow(trace_generator, 236).
    local pow82 = pow7 * pow81;  // pow(trace_generator, 240).
    local pow83 = pow7 * pow82;  // pow(trace_generator, 244).
    local pow84 = pow7 * pow83;  // pow(trace_generator, 248).
    local pow85 = pow7 * pow84;  // pow(trace_generator, 252).
    local pow86 = pow18 * pow85;  // pow(trace_generator, 266).
    local pow87 = pow4 * pow86;  // pow(trace_generator, 267).
    local pow88 = pow4 * pow77;  // pow(trace_generator, 394).
    local pow89 = pow19 * pow88;  // pow(trace_generator, 409).
    local pow90 = pow20 * pow89;  // pow(trace_generator, 425).
    local pow91 = pow28 * pow90;  // pow(trace_generator, 457).
    local pow92 = pow4 * pow91;  // pow(trace_generator, 458).
    local pow93 = pow4 * pow92;  // pow(trace_generator, 459).
    local pow94 = pow18 * pow93;  // pow(trace_generator, 473).
    local pow95 = pow20 * pow94;  // pow(trace_generator, 489).
    local pow96 = pow28 * pow95;  // pow(trace_generator, 521).
    local pow97 = pow28 * pow96;  // pow(trace_generator, 553).
    local pow98 = pow28 * pow97;  // pow(trace_generator, 585).
    local pow99 = pow24 * pow98;  // pow(trace_generator, 609).
    local pow100 = pow20 * pow99;  // pow(trace_generator, 625).
    local pow101 = pow20 * pow100;  // pow(trace_generator, 641).
    local pow102 = pow20 * pow101;  // pow(trace_generator, 657).
    local pow103 = pow84 * pow102;  // pow(trace_generator, 905).
    local pow104 = pow20 * pow102;  // pow(trace_generator, 673).
    local pow105 = pow20 * pow103;  // pow(trace_generator, 921).
    local pow106 = pow20 * pow104;  // pow(trace_generator, 689).
    local pow107 = pow20 * pow105;  // pow(trace_generator, 937).
    local pow108 = pow28 * pow107;  // pow(trace_generator, 969).
    local pow109 = pow25 * pow106;  // pow(trace_generator, 714).
    local pow110 = pow46 * pow109;  // pow(trace_generator, 778).
    local pow111 = pow4 * pow108;  // pow(trace_generator, 970).
    local pow112 = pow3 * pow33;  // pow(trace_generator, 1579).
    local pow113 = pow4 * pow109;  // pow(trace_generator, 715).
    local pow114 = pow4 * pow110;  // pow(trace_generator, 779).
    local pow115 = pow28 * pow86;  // pow(trace_generator, 298).
    local pow116 = pow4 * pow111;  // pow(trace_generator, 971).
    local pow117 = pow15 * pow116;  // pow(trace_generator, 982).
    local pow118 = pow6 * pow117;  // pow(trace_generator, 985).
    local pow119 = pow17 * pow118;  // pow(trace_generator, 998).
    local pow120 = pow6 * pow119;  // pow(trace_generator, 1001).
    local pow121 = pow17 * pow120;  // pow(trace_generator, 1014).
    local pow122 = pow22 * pow121;  // pow(trace_generator, 1034).
    local pow123 = pow2 * pow11;  // pow(trace_generator, 2019).
    local pow124 = pow2 * pow27;  // pow(trace_generator, 2041).
    local pow125 = pow7 * pow124;  // pow(trace_generator, 2045).
    local pow126 = pow2 * pow31;  // pow(trace_generator, 2047).
    local pow127 = pow4 * pow122;  // pow(trace_generator, 1035).
    local pow128 = pow2 * pow32;  // pow(trace_generator, 2049).
    local pow129 = pow2 * pow33;  // pow(trace_generator, 2051).
    local pow130 = pow2 * pow35;  // pow(trace_generator, 2053).
    local pow131 = pow8 * pow130;  // pow(trace_generator, 2058).
    local pow132 = pow2 * pow39;  // pow(trace_generator, 2059).
    local pow133 = pow1 * pow21;  // pow(trace_generator, 4106).

    // Fetch columns.
    tempvar column0 = column_values[0];
    tempvar column1 = column_values[1];
    tempvar column2 = column_values[2];
    tempvar column3 = column_values[3];
    tempvar column4 = column_values[4];
    tempvar column5 = column_values[5];
    tempvar column6 = column_values[6];
    tempvar column7 = column_values[7];

    // Sum the OODS constraints on the trace polynomials.
    tempvar total_sum = 0;

    tempvar value = (column0 - oods_values[0]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[0] * value;

    tempvar value = (column0 - oods_values[1]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[1] * value;

    tempvar value = (column0 - oods_values[2]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[2] * value;

    tempvar value = (column0 - oods_values[3]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[3] * value;

    tempvar value = (column0 - oods_values[4]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[4] * value;

    tempvar value = (column0 - oods_values[5]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[5] * value;

    tempvar value = (column0 - oods_values[6]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[6] * value;

    tempvar value = (column0 - oods_values[7]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    tempvar value = (column0 - oods_values[8]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    tempvar value = (column0 - oods_values[9]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    tempvar value = (column0 - oods_values[10]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    tempvar value = (column0 - oods_values[11]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    tempvar value = (column0 - oods_values[12]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    tempvar value = (column0 - oods_values[13]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    tempvar value = (column0 - oods_values[14]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    tempvar value = (column0 - oods_values[15]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    tempvar value = (column1 - oods_values[16]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    tempvar value = (column1 - oods_values[17]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    tempvar value = (column1 - oods_values[18]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    tempvar value = (column1 - oods_values[19]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    tempvar value = (column1 - oods_values[20]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    tempvar value = (column1 - oods_values[21]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[21] * value;

    tempvar value = (column1 - oods_values[22]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    tempvar value = (column1 - oods_values[23]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    tempvar value = (column1 - oods_values[24]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[24] * value;

    tempvar value = (column1 - oods_values[25]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    tempvar value = (column1 - oods_values[26]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    tempvar value = (column1 - oods_values[27]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    tempvar value = (column1 - oods_values[28]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    tempvar value = (column1 - oods_values[29]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    tempvar value = (column1 - oods_values[30]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    tempvar value = (column1 - oods_values[31]) / (point - pow50 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    tempvar value = (column1 - oods_values[32]) / (point - pow51 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    tempvar value = (column1 - oods_values[33]) / (point - pow57 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    tempvar value = (column1 - oods_values[34]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    tempvar value = (column1 - oods_values[35]) / (point - pow63 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    tempvar value = (column1 - oods_values[36]) / (point - pow65 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    tempvar value = (column1 - oods_values[37]) / (point - pow75 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    tempvar value = (column1 - oods_values[38]) / (point - pow76 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    tempvar value = (column1 - oods_values[39]) / (point - pow79 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    tempvar value = (column1 - oods_values[40]) / (point - pow80 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    tempvar value = (column1 - oods_values[41]) / (point - pow86 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    tempvar value = (column1 - oods_values[42]) / (point - pow87 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    tempvar value = (column1 - oods_values[43]) / (point - pow115 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    tempvar value = (column1 - oods_values[44]) / (point - pow88 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    tempvar value = (column1 - oods_values[45]) / (point - pow92 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    tempvar value = (column1 - oods_values[46]) / (point - pow93 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    tempvar value = (column1 - oods_values[47]) / (point - pow109 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    tempvar value = (column1 - oods_values[48]) / (point - pow113 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    tempvar value = (column1 - oods_values[49]) / (point - pow110 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    tempvar value = (column1 - oods_values[50]) / (point - pow114 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    tempvar value = (column1 - oods_values[51]) / (point - pow111 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    tempvar value = (column1 - oods_values[52]) / (point - pow116 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    tempvar value = (column1 - oods_values[53]) / (point - pow122 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    tempvar value = (column1 - oods_values[54]) / (point - pow127 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    tempvar value = (column1 - oods_values[55]) / (point - pow131 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    tempvar value = (column1 - oods_values[56]) / (point - pow132 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    tempvar value = (column1 - oods_values[57]) / (point - pow133 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    tempvar value = (column2 - oods_values[58]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    tempvar value = (column2 - oods_values[59]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    tempvar value = (column2 - oods_values[60]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    tempvar value = (column2 - oods_values[61]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    tempvar value = (column3 - oods_values[62]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    tempvar value = (column3 - oods_values[63]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    tempvar value = (column3 - oods_values[64]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    tempvar value = (column3 - oods_values[65]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    tempvar value = (column3 - oods_values[66]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    tempvar value = (column3 - oods_values[67]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    tempvar value = (column3 - oods_values[68]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    tempvar value = (column3 - oods_values[69]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    tempvar value = (column3 - oods_values[70]) / (point - pow22 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    tempvar value = (column3 - oods_values[71]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    tempvar value = (column3 - oods_values[72]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    tempvar value = (column3 - oods_values[73]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    tempvar value = (column3 - oods_values[74]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    tempvar value = (column3 - oods_values[75]) / (point - pow33 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    tempvar value = (column3 - oods_values[76]) / (point - pow37 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    tempvar value = (column3 - oods_values[77]) / (point - pow39 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    tempvar value = (column3 - oods_values[78]) / (point - pow41 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    tempvar value = (column3 - oods_values[79]) / (point - pow43 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    tempvar value = (column3 - oods_values[80]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    tempvar value = (column3 - oods_values[81]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    tempvar value = (column3 - oods_values[82]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    tempvar value = (column3 - oods_values[83]) / (point - pow59 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    tempvar value = (column3 - oods_values[84]) / (point - pow60 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    tempvar value = (column3 - oods_values[85]) / (point - pow68 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    tempvar value = (column3 - oods_values[86]) / (point - pow69 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    tempvar value = (column3 - oods_values[87]) / (point - pow70 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    tempvar value = (column3 - oods_values[88]) / (point - pow71 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    tempvar value = (column3 - oods_values[89]) / (point - pow72 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    tempvar value = (column3 - oods_values[90]) / (point - pow73 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    tempvar value = (column3 - oods_values[91]) / (point - pow82 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    tempvar value = (column3 - oods_values[92]) / (point - pow83 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    tempvar value = (column3 - oods_values[93]) / (point - pow84 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    tempvar value = (column3 - oods_values[94]) / (point - pow85 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    tempvar value = (column4 - oods_values[95]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    tempvar value = (column4 - oods_values[96]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    tempvar value = (column4 - oods_values[97]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    tempvar value = (column4 - oods_values[98]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    tempvar value = (column4 - oods_values[99]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    tempvar value = (column4 - oods_values[100]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    tempvar value = (column4 - oods_values[101]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    tempvar value = (column4 - oods_values[102]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    tempvar value = (column4 - oods_values[103]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    tempvar value = (column4 - oods_values[104]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    tempvar value = (column4 - oods_values[105]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    tempvar value = (column4 - oods_values[106]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    tempvar value = (column4 - oods_values[107]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    tempvar value = (column4 - oods_values[108]) / (point - pow37 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    tempvar value = (column4 - oods_values[109]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    tempvar value = (column4 - oods_values[110]) / (point - pow58 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    tempvar value = (column4 - oods_values[111]) / (point - pow66 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    tempvar value = (column4 - oods_values[112]) / (point - pow67 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    tempvar value = (column4 - oods_values[113]) / (point - pow78 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    tempvar value = (column4 - oods_values[114]) / (point - pow81 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    tempvar value = (column4 - oods_values[115]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    tempvar value = (column4 - oods_values[116]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    tempvar value = (column4 - oods_values[117]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    tempvar value = (column4 - oods_values[118]) / (point - pow112 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    tempvar value = (column4 - oods_values[119]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    tempvar value = (column4 - oods_values[120]) / (point - pow123 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    tempvar value = (column4 - oods_values[121]) / (point - pow124 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    tempvar value = (column4 - oods_values[122]) / (point - pow125 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    tempvar value = (column4 - oods_values[123]) / (point - pow126 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    tempvar value = (column4 - oods_values[124]) / (point - pow128 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    tempvar value = (column4 - oods_values[125]) / (point - pow129 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    tempvar value = (column4 - oods_values[126]) / (point - pow130 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    tempvar value = (column4 - oods_values[127]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    tempvar value = (column5 - oods_values[128]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    tempvar value = (column5 - oods_values[129]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    tempvar value = (column5 - oods_values[130]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    tempvar value = (column5 - oods_values[131]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    tempvar value = (column5 - oods_values[132]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    tempvar value = (column5 - oods_values[133]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

    tempvar value = (column5 - oods_values[134]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[134] * value;

    tempvar value = (column5 - oods_values[135]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[135] * value;

    tempvar value = (column5 - oods_values[136]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[136] * value;

    tempvar value = (column5 - oods_values[137]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[137] * value;

    tempvar value = (column5 - oods_values[138]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[138] * value;

    tempvar value = (column5 - oods_values[139]) / (point - pow21 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[139] * value;

    tempvar value = (column5 - oods_values[140]) / (point - pow23 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[140] * value;

    tempvar value = (column5 - oods_values[141]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[141] * value;

    tempvar value = (column5 - oods_values[142]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[142] * value;

    tempvar value = (column5 - oods_values[143]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[143] * value;

    tempvar value = (column5 - oods_values[144]) / (point - pow29 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[144] * value;

    tempvar value = (column5 - oods_values[145]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[145] * value;

    tempvar value = (column5 - oods_values[146]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[146] * value;

    tempvar value = (column5 - oods_values[147]) / (point - pow38 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[147] * value;

    tempvar value = (column5 - oods_values[148]) / (point - pow40 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[148] * value;

    tempvar value = (column5 - oods_values[149]) / (point - pow42 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[149] * value;

    tempvar value = (column5 - oods_values[150]) / (point - pow44 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[150] * value;

    tempvar value = (column5 - oods_values[151]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[151] * value;

    tempvar value = (column5 - oods_values[152]) / (point - pow49 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[152] * value;

    tempvar value = (column5 - oods_values[153]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[153] * value;

    tempvar value = (column5 - oods_values[154]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[154] * value;

    tempvar value = (column5 - oods_values[155]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[155] * value;

    tempvar value = (column5 - oods_values[156]) / (point - pow56 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[156] * value;

    tempvar value = (column5 - oods_values[157]) / (point - pow61 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[157] * value;

    tempvar value = (column5 - oods_values[158]) / (point - pow64 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[158] * value;

    tempvar value = (column5 - oods_values[159]) / (point - pow74 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[159] * value;

    tempvar value = (column5 - oods_values[160]) / (point - pow77 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[160] * value;

    tempvar value = (column5 - oods_values[161]) / (point - pow89 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[161] * value;

    tempvar value = (column5 - oods_values[162]) / (point - pow90 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[162] * value;

    tempvar value = (column5 - oods_values[163]) / (point - pow91 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[163] * value;

    tempvar value = (column5 - oods_values[164]) / (point - pow94 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[164] * value;

    tempvar value = (column5 - oods_values[165]) / (point - pow95 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[165] * value;

    tempvar value = (column5 - oods_values[166]) / (point - pow96 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[166] * value;

    tempvar value = (column5 - oods_values[167]) / (point - pow97 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[167] * value;

    tempvar value = (column5 - oods_values[168]) / (point - pow98 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[168] * value;

    tempvar value = (column5 - oods_values[169]) / (point - pow99 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[169] * value;

    tempvar value = (column5 - oods_values[170]) / (point - pow100 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[170] * value;

    tempvar value = (column5 - oods_values[171]) / (point - pow101 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[171] * value;

    tempvar value = (column5 - oods_values[172]) / (point - pow102 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[172] * value;

    tempvar value = (column5 - oods_values[173]) / (point - pow104 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[173] * value;

    tempvar value = (column5 - oods_values[174]) / (point - pow106 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[174] * value;

    tempvar value = (column5 - oods_values[175]) / (point - pow103 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[175] * value;

    tempvar value = (column5 - oods_values[176]) / (point - pow105 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[176] * value;

    tempvar value = (column5 - oods_values[177]) / (point - pow107 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[177] * value;

    tempvar value = (column5 - oods_values[178]) / (point - pow108 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[178] * value;

    tempvar value = (column5 - oods_values[179]) / (point - pow117 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[179] * value;

    tempvar value = (column5 - oods_values[180]) / (point - pow118 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[180] * value;

    tempvar value = (column5 - oods_values[181]) / (point - pow119 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[181] * value;

    tempvar value = (column5 - oods_values[182]) / (point - pow120 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[182] * value;

    tempvar value = (column5 - oods_values[183]) / (point - pow121 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[183] * value;

    tempvar value = (column6 - oods_values[184]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[184] * value;

    tempvar value = (column6 - oods_values[185]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[185] * value;

    tempvar value = (column6 - oods_values[186]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[186] * value;

    tempvar value = (column6 - oods_values[187]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[187] * value;

    tempvar value = (column7 - oods_values[188]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[188] * value;

    tempvar value = (column7 - oods_values[189]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[189] * value;

    tempvar value = (column7 - oods_values[190]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[190] * value;

    tempvar value = (column7 - oods_values[191]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[191] * value;

    // Sum the OODS boundary constraints on the composition polynomials.
    let (oods_point_to_deg) = pow(oods_point, CONSTRAINT_DEGREE);

    tempvar value = (column_values[NUM_COLUMNS_FIRST + NUM_COLUMNS_SECOND] - oods_values[192]) / (
        point - oods_point_to_deg
    );
    tempvar total_sum = total_sum + constraint_coefficients[192] * value;

    tempvar value = (column_values[NUM_COLUMNS_FIRST + NUM_COLUMNS_SECOND + 1] - oods_values[193]) /
        (point - oods_point_to_deg);
    tempvar total_sum = total_sum + constraint_coefficients[193] * value;

    static_assert 194 == MASK_SIZE + CONSTRAINT_DEGREE;
    return (res=total_sum);
}
