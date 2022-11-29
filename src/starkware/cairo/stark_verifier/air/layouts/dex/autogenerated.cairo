from starkware.cairo.stark_verifier.air.layouts.dex.global_values import GlobalValues
from starkware.cairo.stark_verifier.air.oods import OodsGlobalValues
from starkware.cairo.common.pow import pow

const N_CONSTRAINTS = 179;
const MASK_SIZE = 200;
const N_ORIGINAL_COLUMNS = 21;
const N_INTERACTION_COLUMNS = 1;
const PUBLIC_MEMORY_STEP = 8;
const HAS_DILUTED_POOL = 0;
const PEDERSEN_BUILTIN_RATIO = 8;
const PEDERSEN_BUILTIN_REPETITIONS = 4;
const RC_BUILTIN_RATIO = 8;
const RC_N_PARTS = 8;
const ECDSA_BUILTIN_RATIO = 512;
const ECDSA_BUILTIN_REPETITIONS = 1;
const ECDSA_ELEMENT_BITS = 251;
const ECDSA_ELEMENT_HEIGHT = 256;
const HAS_OUTPUT_BUILTIN = 1;
const HAS_PEDERSEN_BUILTIN = 1;
const HAS_RANGE_CHECK_BUILTIN = 1;
const HAS_ECDSA_BUILTIN = 1;
const HAS_BITWISE_BUILTIN = 0;
const HAS_KECCAK_BUILTIN = 0;
const HAS_EC_OP_BUILTIN = 0;
const LAYOUT_CODE = 0x646578;
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
    let (local pow0) = pow(point, global_values.trace_length / 8192);
    local pow1 = pow0 * pow0;
    let (local pow2) = pow(point, global_values.trace_length / 512);
    local pow3 = pow2 * pow2;
    local pow4 = pow3 * pow3;
    let (local pow5) = pow(point, global_values.trace_length / 32);
    local pow6 = pow5 * pow5;
    local pow7 = pow6 * pow6;
    local pow8 = pow7 * pow7;
    local pow9 = pow8 * pow8;
    local pow10 = pow9 * pow9;
    let (local pow11) = pow(trace_generator, global_values.trace_length / 2);
    let (local pow12) = pow(trace_generator, 15 * global_values.trace_length / 16);
    let (local pow13) = pow(trace_generator, 251 * global_values.trace_length / 256);
    let (local pow14) = pow(trace_generator, 63 * global_values.trace_length / 64);
    let (local pow15) = pow(trace_generator, 255 * global_values.trace_length / 256);
    let (local pow16) = pow(trace_generator, 16 * (global_values.trace_length / 16 - 1));
    let (local pow17) = pow(trace_generator, 2 * (global_values.trace_length / 2 - 1));
    let (local pow18) = pow(trace_generator, 4 * (global_values.trace_length / 4 - 1));
    let (local pow19) = pow(trace_generator, 128 * (global_values.trace_length / 128 - 1));
    let (local pow20) = pow(trace_generator, 8192 * (global_values.trace_length / 8192 - 1));

    // Compute domains.
    tempvar domain0 = pow10 - 1;
    tempvar domain1 = pow9 - 1;
    tempvar domain2 = pow8 - 1;
    tempvar domain3 = pow7 - 1;
    tempvar domain4 = pow6 - pow12;
    tempvar domain5 = pow6 - 1;
    tempvar domain6 = pow5 - 1;
    tempvar domain7 = pow4 - 1;
    tempvar domain8 = pow3 - 1;
    tempvar domain9 = pow3 - pow15;
    tempvar domain10 = pow3 - pow14;
    tempvar domain11 = pow2 - pow11;
    tempvar domain12 = pow2 - 1;
    tempvar domain13 = pow1 - pow15;
    tempvar domain14 = pow1 - pow13;
    tempvar domain15 = pow1 - 1;
    tempvar domain16 = pow0 - pow15;
    tempvar domain17 = pow0 - pow13;
    tempvar domain18 = pow0 - 1;
    tempvar domain19 = point - pow16;
    tempvar domain20 = point - 1;
    tempvar domain21 = point - pow17;
    tempvar domain22 = point - pow18;
    tempvar domain23 = point - pow19;
    tempvar domain24 = point - pow20;

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
    tempvar column1_row255 = mask_values[18];
    tempvar column1_row256 = mask_values[19];
    tempvar column1_row511 = mask_values[20];
    tempvar column2_row0 = mask_values[21];
    tempvar column2_row1 = mask_values[22];
    tempvar column2_row255 = mask_values[23];
    tempvar column2_row256 = mask_values[24];
    tempvar column3_row0 = mask_values[25];
    tempvar column3_row1 = mask_values[26];
    tempvar column3_row192 = mask_values[27];
    tempvar column3_row193 = mask_values[28];
    tempvar column3_row196 = mask_values[29];
    tempvar column3_row197 = mask_values[30];
    tempvar column3_row251 = mask_values[31];
    tempvar column3_row252 = mask_values[32];
    tempvar column3_row256 = mask_values[33];
    tempvar column4_row0 = mask_values[34];
    tempvar column4_row1 = mask_values[35];
    tempvar column4_row255 = mask_values[36];
    tempvar column4_row256 = mask_values[37];
    tempvar column4_row511 = mask_values[38];
    tempvar column5_row0 = mask_values[39];
    tempvar column5_row1 = mask_values[40];
    tempvar column5_row255 = mask_values[41];
    tempvar column5_row256 = mask_values[42];
    tempvar column6_row0 = mask_values[43];
    tempvar column6_row1 = mask_values[44];
    tempvar column6_row192 = mask_values[45];
    tempvar column6_row193 = mask_values[46];
    tempvar column6_row196 = mask_values[47];
    tempvar column6_row197 = mask_values[48];
    tempvar column6_row251 = mask_values[49];
    tempvar column6_row252 = mask_values[50];
    tempvar column6_row256 = mask_values[51];
    tempvar column7_row0 = mask_values[52];
    tempvar column7_row1 = mask_values[53];
    tempvar column7_row255 = mask_values[54];
    tempvar column7_row256 = mask_values[55];
    tempvar column7_row511 = mask_values[56];
    tempvar column8_row0 = mask_values[57];
    tempvar column8_row1 = mask_values[58];
    tempvar column8_row255 = mask_values[59];
    tempvar column8_row256 = mask_values[60];
    tempvar column9_row0 = mask_values[61];
    tempvar column9_row1 = mask_values[62];
    tempvar column9_row192 = mask_values[63];
    tempvar column9_row193 = mask_values[64];
    tempvar column9_row196 = mask_values[65];
    tempvar column9_row197 = mask_values[66];
    tempvar column9_row251 = mask_values[67];
    tempvar column9_row252 = mask_values[68];
    tempvar column9_row256 = mask_values[69];
    tempvar column10_row0 = mask_values[70];
    tempvar column10_row1 = mask_values[71];
    tempvar column10_row255 = mask_values[72];
    tempvar column10_row256 = mask_values[73];
    tempvar column10_row511 = mask_values[74];
    tempvar column11_row0 = mask_values[75];
    tempvar column11_row1 = mask_values[76];
    tempvar column11_row255 = mask_values[77];
    tempvar column11_row256 = mask_values[78];
    tempvar column12_row0 = mask_values[79];
    tempvar column12_row1 = mask_values[80];
    tempvar column12_row192 = mask_values[81];
    tempvar column12_row193 = mask_values[82];
    tempvar column12_row196 = mask_values[83];
    tempvar column12_row197 = mask_values[84];
    tempvar column12_row251 = mask_values[85];
    tempvar column12_row252 = mask_values[86];
    tempvar column12_row256 = mask_values[87];
    tempvar column13_row0 = mask_values[88];
    tempvar column13_row255 = mask_values[89];
    tempvar column14_row0 = mask_values[90];
    tempvar column14_row255 = mask_values[91];
    tempvar column15_row0 = mask_values[92];
    tempvar column15_row255 = mask_values[93];
    tempvar column16_row0 = mask_values[94];
    tempvar column16_row255 = mask_values[95];
    tempvar column17_row0 = mask_values[96];
    tempvar column17_row1 = mask_values[97];
    tempvar column17_row2 = mask_values[98];
    tempvar column17_row3 = mask_values[99];
    tempvar column17_row4 = mask_values[100];
    tempvar column17_row5 = mask_values[101];
    tempvar column17_row6 = mask_values[102];
    tempvar column17_row7 = mask_values[103];
    tempvar column17_row8 = mask_values[104];
    tempvar column17_row9 = mask_values[105];
    tempvar column17_row12 = mask_values[106];
    tempvar column17_row13 = mask_values[107];
    tempvar column17_row16 = mask_values[108];
    tempvar column17_row22 = mask_values[109];
    tempvar column17_row23 = mask_values[110];
    tempvar column17_row38 = mask_values[111];
    tempvar column17_row39 = mask_values[112];
    tempvar column17_row70 = mask_values[113];
    tempvar column17_row71 = mask_values[114];
    tempvar column17_row102 = mask_values[115];
    tempvar column17_row103 = mask_values[116];
    tempvar column17_row134 = mask_values[117];
    tempvar column17_row135 = mask_values[118];
    tempvar column17_row167 = mask_values[119];
    tempvar column17_row199 = mask_values[120];
    tempvar column17_row230 = mask_values[121];
    tempvar column17_row263 = mask_values[122];
    tempvar column17_row295 = mask_values[123];
    tempvar column17_row327 = mask_values[124];
    tempvar column17_row391 = mask_values[125];
    tempvar column17_row423 = mask_values[126];
    tempvar column17_row455 = mask_values[127];
    tempvar column17_row4118 = mask_values[128];
    tempvar column17_row4119 = mask_values[129];
    tempvar column17_row8214 = mask_values[130];
    tempvar column18_row0 = mask_values[131];
    tempvar column18_row1 = mask_values[132];
    tempvar column18_row2 = mask_values[133];
    tempvar column18_row3 = mask_values[134];
    tempvar column19_row0 = mask_values[135];
    tempvar column19_row1 = mask_values[136];
    tempvar column19_row2 = mask_values[137];
    tempvar column19_row3 = mask_values[138];
    tempvar column19_row4 = mask_values[139];
    tempvar column19_row5 = mask_values[140];
    tempvar column19_row6 = mask_values[141];
    tempvar column19_row7 = mask_values[142];
    tempvar column19_row8 = mask_values[143];
    tempvar column19_row9 = mask_values[144];
    tempvar column19_row11 = mask_values[145];
    tempvar column19_row12 = mask_values[146];
    tempvar column19_row13 = mask_values[147];
    tempvar column19_row15 = mask_values[148];
    tempvar column19_row17 = mask_values[149];
    tempvar column19_row23 = mask_values[150];
    tempvar column19_row25 = mask_values[151];
    tempvar column19_row28 = mask_values[152];
    tempvar column19_row31 = mask_values[153];
    tempvar column19_row44 = mask_values[154];
    tempvar column19_row60 = mask_values[155];
    tempvar column19_row76 = mask_values[156];
    tempvar column19_row92 = mask_values[157];
    tempvar column19_row108 = mask_values[158];
    tempvar column19_row124 = mask_values[159];
    tempvar column19_row4103 = mask_values[160];
    tempvar column19_row4111 = mask_values[161];
    tempvar column20_row0 = mask_values[162];
    tempvar column20_row1 = mask_values[163];
    tempvar column20_row2 = mask_values[164];
    tempvar column20_row4 = mask_values[165];
    tempvar column20_row6 = mask_values[166];
    tempvar column20_row8 = mask_values[167];
    tempvar column20_row10 = mask_values[168];
    tempvar column20_row12 = mask_values[169];
    tempvar column20_row14 = mask_values[170];
    tempvar column20_row16 = mask_values[171];
    tempvar column20_row17 = mask_values[172];
    tempvar column20_row20 = mask_values[173];
    tempvar column20_row22 = mask_values[174];
    tempvar column20_row24 = mask_values[175];
    tempvar column20_row30 = mask_values[176];
    tempvar column20_row38 = mask_values[177];
    tempvar column20_row46 = mask_values[178];
    tempvar column20_row54 = mask_values[179];
    tempvar column20_row81 = mask_values[180];
    tempvar column20_row145 = mask_values[181];
    tempvar column20_row209 = mask_values[182];
    tempvar column20_row4080 = mask_values[183];
    tempvar column20_row4082 = mask_values[184];
    tempvar column20_row4088 = mask_values[185];
    tempvar column20_row4090 = mask_values[186];
    tempvar column20_row4092 = mask_values[187];
    tempvar column20_row8161 = mask_values[188];
    tempvar column20_row8166 = mask_values[189];
    tempvar column20_row8176 = mask_values[190];
    tempvar column20_row8178 = mask_values[191];
    tempvar column20_row8182 = mask_values[192];
    tempvar column20_row8184 = mask_values[193];
    tempvar column20_row8186 = mask_values[194];
    tempvar column20_row8190 = mask_values[195];
    tempvar column21_inter1_row0 = mask_values[196];
    tempvar column21_inter1_row1 = mask_values[197];
    tempvar column21_inter1_row2 = mask_values[198];
    tempvar column21_inter1_row5 = mask_values[199];

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
    tempvar npc_reg_0 = column17_row0 + cpu__decode__opcode_rc__bit_2 + 1;
    tempvar cpu__decode__opcode_rc__bit_10 = column0_row10 - (column0_row11 + column0_row11);
    tempvar cpu__decode__opcode_rc__bit_11 = column0_row11 - (column0_row12 + column0_row12);
    tempvar cpu__decode__opcode_rc__bit_14 = column0_row14 - (column0_row15 + column0_row15);
    tempvar memory__address_diff_0 = column18_row2 - column18_row0;
    tempvar rc16__diff_0 = column19_row6 - column19_row2;
    tempvar pedersen__hash0__ec_subset_sum__bit_0 = column3_row0 - (column3_row1 + column3_row1);
    tempvar pedersen__hash0__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash0__ec_subset_sum__bit_0;
    tempvar pedersen__hash1__ec_subset_sum__bit_0 = column6_row0 - (column6_row1 + column6_row1);
    tempvar pedersen__hash1__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash1__ec_subset_sum__bit_0;
    tempvar pedersen__hash2__ec_subset_sum__bit_0 = column9_row0 - (column9_row1 + column9_row1);
    tempvar pedersen__hash2__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash2__ec_subset_sum__bit_0;
    tempvar pedersen__hash3__ec_subset_sum__bit_0 = column12_row0 - (column12_row1 + column12_row1);
    tempvar pedersen__hash3__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash3__ec_subset_sum__bit_0;
    tempvar rc_builtin__value0_0 = column19_row12;
    tempvar rc_builtin__value1_0 = rc_builtin__value0_0 * global_values.offset_size +
        column19_row28;
    tempvar rc_builtin__value2_0 = rc_builtin__value1_0 * global_values.offset_size +
        column19_row44;
    tempvar rc_builtin__value3_0 = rc_builtin__value2_0 * global_values.offset_size +
        column19_row60;
    tempvar rc_builtin__value4_0 = rc_builtin__value3_0 * global_values.offset_size +
        column19_row76;
    tempvar rc_builtin__value5_0 = rc_builtin__value4_0 * global_values.offset_size +
        column19_row92;
    tempvar rc_builtin__value6_0 = rc_builtin__value5_0 * global_values.offset_size +
        column19_row108;
    tempvar rc_builtin__value7_0 = rc_builtin__value6_0 * global_values.offset_size +
        column19_row124;
    tempvar ecdsa__signature0__doubling_key__x_squared = column19_row7 * column19_row7;
    tempvar ecdsa__signature0__exponentiate_generator__bit_0 = column20_row14 - (
        column20_row46 + column20_row46
    );
    tempvar ecdsa__signature0__exponentiate_generator__bit_neg_0 = 1 -
        ecdsa__signature0__exponentiate_generator__bit_0;
    tempvar ecdsa__signature0__exponentiate_key__bit_0 = column20_row4 - (
        column20_row20 + column20_row20
    );
    tempvar ecdsa__signature0__exponentiate_key__bit_neg_0 = 1 -
        ecdsa__signature0__exponentiate_key__bit_0;

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
        column17_row1 -
        (
            (
                (column0_row0 * global_values.offset_size + column19_row4) *
                global_values.offset_size +
                column19_row8
            ) * global_values.offset_size +
            column19_row0
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
        column17_row8 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_rc__bit_0 * column19_row9 +
            (1 - cpu__decode__opcode_rc__bit_0) * column19_row1 +
            column19_row0
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    // Constraint: cpu/operands/mem0_addr.
    tempvar value = (
        column17_row4 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_rc__bit_1 * column19_row9 +
            (1 - cpu__decode__opcode_rc__bit_1) * column19_row1 +
            column19_row8
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    // Constraint: cpu/operands/mem1_addr.
    tempvar value = (
        column17_row12 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_rc__bit_2 * column17_row0 +
            cpu__decode__opcode_rc__bit_4 * column19_row1 +
            cpu__decode__opcode_rc__bit_3 * column19_row9 +
            cpu__decode__flag_op1_base_op0_0 * column17_row5 +
            column19_row4
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    // Constraint: cpu/operands/ops_mul.
    tempvar value = (column19_row5 - column17_row5 * column17_row13) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    // Constraint: cpu/operands/res.
    tempvar value = (
        (1 - cpu__decode__opcode_rc__bit_9) * column19_row13 -
        (
            cpu__decode__opcode_rc__bit_5 * (column17_row5 + column17_row13) +
            cpu__decode__opcode_rc__bit_6 * column19_row5 +
            cpu__decode__flag_res_op1_0 * column17_row13
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    // Constraint: cpu/update_registers/update_pc/tmp0.
    tempvar value = (column19_row3 - cpu__decode__opcode_rc__bit_9 * column17_row9) * domain19 /
        domain5;
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    // Constraint: cpu/update_registers/update_pc/tmp1.
    tempvar value = (column19_row11 - column19_row3 * column19_row13) * domain19 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_negative.
    tempvar value = (
        (1 - cpu__decode__opcode_rc__bit_9) * column17_row16 +
        column19_row3 * (column17_row16 - (column17_row0 + column17_row13)) -
        (
            cpu__decode__flag_pc_update_regular_0 * npc_reg_0 +
            cpu__decode__opcode_rc__bit_7 * column19_row13 +
            cpu__decode__opcode_rc__bit_8 * (column17_row0 + column19_row13)
        )
    ) * domain19 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_positive.
    tempvar value = (
        (column19_row11 - cpu__decode__opcode_rc__bit_9) * (column17_row16 - npc_reg_0)
    ) * domain19 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    // Constraint: cpu/update_registers/update_ap/ap_update.
    tempvar value = (
        column19_row17 -
        (
            column19_row1 +
            cpu__decode__opcode_rc__bit_10 * column19_row13 +
            cpu__decode__opcode_rc__bit_11 +
            cpu__decode__opcode_rc__bit_12 * 2
        )
    ) * domain19 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    // Constraint: cpu/update_registers/update_fp/fp_update.
    tempvar value = (
        column19_row25 -
        (
            cpu__decode__fp_update_regular_0 * column19_row9 +
            cpu__decode__opcode_rc__bit_13 * column17_row9 +
            cpu__decode__opcode_rc__bit_12 * (column19_row1 + 2)
        )
    ) * domain19 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    // Constraint: cpu/opcodes/call/push_fp.
    tempvar value = (cpu__decode__opcode_rc__bit_12 * (column17_row9 - column19_row9)) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    // Constraint: cpu/opcodes/call/push_pc.
    tempvar value = (
        cpu__decode__opcode_rc__bit_12 * (
            column17_row5 - (column17_row0 + cpu__decode__opcode_rc__bit_2 + 1)
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    // Constraint: cpu/opcodes/call/off0.
    tempvar value = (
        cpu__decode__opcode_rc__bit_12 * (column19_row0 - global_values.half_offset_size)
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    // Constraint: cpu/opcodes/call/off1.
    tempvar value = (
        cpu__decode__opcode_rc__bit_12 * (column19_row8 - (global_values.half_offset_size + 1))
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
        cpu__decode__opcode_rc__bit_13 * (column19_row0 + 2 - global_values.half_offset_size)
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    // Constraint: cpu/opcodes/ret/off2.
    tempvar value = (
        cpu__decode__opcode_rc__bit_13 * (column19_row4 + 1 - global_values.half_offset_size)
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
    tempvar value = (cpu__decode__opcode_rc__bit_14 * (column17_row9 - column19_row13)) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    // Constraint: initial_ap.
    tempvar value = (column19_row1 - global_values.initial_ap) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    // Constraint: initial_fp.
    tempvar value = (column19_row9 - global_values.initial_ap) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    // Constraint: initial_pc.
    tempvar value = (column17_row0 - global_values.initial_pc) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    // Constraint: final_ap.
    tempvar value = (column19_row1 - global_values.final_ap) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    // Constraint: final_fp.
    tempvar value = (column19_row9 - global_values.initial_ap) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    // Constraint: final_pc.
    tempvar value = (column17_row0 - global_values.final_pc) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    // Constraint: memory/multi_column_perm/perm/init0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column18_row0 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column18_row1
            )
        ) * column21_inter1_row0 +
        column17_row0 +
        global_values.memory__multi_column_perm__hash_interaction_elm0 * column17_row1 -
        global_values.memory__multi_column_perm__perm__interaction_elm
    ) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    // Constraint: memory/multi_column_perm/perm/step0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column18_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column18_row3
            )
        ) * column21_inter1_row2 -
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column17_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column17_row3
            )
        ) * column21_inter1_row0
    ) * domain21 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    // Constraint: memory/multi_column_perm/perm/last.
    tempvar value = (
        column21_inter1_row0 - global_values.memory__multi_column_perm__perm__public_memory_prod
    ) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    // Constraint: memory/diff_is_bit.
    tempvar value = (memory__address_diff_0 * memory__address_diff_0 - memory__address_diff_0) *
        domain21 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    // Constraint: memory/is_func.
    tempvar value = ((memory__address_diff_0 - 1) * (column18_row1 - column18_row3)) * domain21 /
        domain1;
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    // Constraint: memory/initial_addr.
    tempvar value = (column18_row0 - 1) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    // Constraint: public_memory_addr_zero.
    tempvar value = (column17_row2) / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    // Constraint: public_memory_value_zero.
    tempvar value = (column17_row3) / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    // Constraint: rc16/perm/init0.
    tempvar value = (
        (global_values.rc16__perm__interaction_elm - column19_row2) * column21_inter1_row1 +
        column19_row0 -
        global_values.rc16__perm__interaction_elm
    ) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    // Constraint: rc16/perm/step0.
    tempvar value = (
        (global_values.rc16__perm__interaction_elm - column19_row6) * column21_inter1_row5 -
        (global_values.rc16__perm__interaction_elm - column19_row4) * column21_inter1_row1
    ) * domain22 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    // Constraint: rc16/perm/last.
    tempvar value = (column21_inter1_row1 - global_values.rc16__perm__public_memory_prod) /
        domain22;
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    // Constraint: rc16/diff_is_bit.
    tempvar value = (rc16__diff_0 * rc16__diff_0 - rc16__diff_0) * domain22 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    // Constraint: rc16/minimum.
    tempvar value = (column19_row2 - global_values.rc_min) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    // Constraint: rc16/maximum.
    tempvar value = (column19_row2 - global_values.rc_max) / domain22;
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column14_row255 * (column3_row0 - (column3_row1 + column3_row1))) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column14_row255 * (
            column3_row1 -
            3138550867693340381917894711603833208051177722232017256448 * column3_row192
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column14_row255 - column13_row255 * (column3_row192 - (column3_row193 + column3_row193))
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column13_row255 * (column3_row193 - 8 * column3_row196)) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column13_row255 -
        (column3_row251 - (column3_row252 + column3_row252)) * (
            column3_row196 - (column3_row197 + column3_row197)
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column3_row251 - (column3_row252 + column3_row252)) * (
            column3_row197 - 18014398509481984 * column3_row251
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (pedersen__hash0__ec_subset_sum__bit_0 - 1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_extraction_end.
    tempvar value = (column3_row0) / domain10;
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/zeros_tail.
    tempvar value = (column3_row0) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column2_row0 - global_values.pedersen__points__y) -
        column13_row0 * (column1_row0 - global_values.pedersen__points__x)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/x.
    tempvar value = (
        column13_row0 * column13_row0 -
        pedersen__hash0__ec_subset_sum__bit_0 * (
            column1_row0 + global_values.pedersen__points__x + column1_row1
        )
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column2_row0 + column2_row1) -
        column13_row0 * (column1_row0 - column1_row1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column1_row1 - column1_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column2_row1 - column2_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    // Constraint: pedersen/hash0/copy_point/x.
    tempvar value = (column1_row256 - column1_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    // Constraint: pedersen/hash0/copy_point/y.
    tempvar value = (column2_row256 - column2_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    // Constraint: pedersen/hash0/init/x.
    tempvar value = (column1_row0 - global_values.pedersen__shift_point.x) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    // Constraint: pedersen/hash0/init/y.
    tempvar value = (column2_row0 - global_values.pedersen__shift_point.y) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column16_row255 * (column6_row0 - (column6_row1 + column6_row1))) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column16_row255 * (
            column6_row1 -
            3138550867693340381917894711603833208051177722232017256448 * column6_row192
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column16_row255 - column15_row255 * (column6_row192 - (column6_row193 + column6_row193))
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column15_row255 * (column6_row193 - 8 * column6_row196)) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column15_row255 -
        (column6_row251 - (column6_row252 + column6_row252)) * (
            column6_row196 - (column6_row197 + column6_row197)
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column6_row251 - (column6_row252 + column6_row252)) * (
            column6_row197 - 18014398509481984 * column6_row251
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash1__ec_subset_sum__bit_0 * (pedersen__hash1__ec_subset_sum__bit_0 - 1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/bit_extraction_end.
    tempvar value = (column6_row0) / domain10;
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/zeros_tail.
    tempvar value = (column6_row0) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash1__ec_subset_sum__bit_0 * (column5_row0 - global_values.pedersen__points__y) -
        column14_row0 * (column4_row0 - global_values.pedersen__points__x)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/add_points/x.
    tempvar value = (
        column14_row0 * column14_row0 -
        pedersen__hash1__ec_subset_sum__bit_0 * (
            column4_row0 + global_values.pedersen__points__x + column4_row1
        )
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash1__ec_subset_sum__bit_0 * (column5_row0 + column5_row1) -
        column14_row0 * (column4_row0 - column4_row1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash1__ec_subset_sum__bit_neg_0 * (column4_row1 - column4_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    // Constraint: pedersen/hash1/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash1__ec_subset_sum__bit_neg_0 * (column5_row1 - column5_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    // Constraint: pedersen/hash1/copy_point/x.
    tempvar value = (column4_row256 - column4_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    // Constraint: pedersen/hash1/copy_point/y.
    tempvar value = (column5_row256 - column5_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    // Constraint: pedersen/hash1/init/x.
    tempvar value = (column4_row0 - global_values.pedersen__shift_point.x) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    // Constraint: pedersen/hash1/init/y.
    tempvar value = (column5_row0 - global_values.pedersen__shift_point.y) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column20_row145 * (column9_row0 - (column9_row1 + column9_row1))) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column20_row145 * (
            column9_row1 -
            3138550867693340381917894711603833208051177722232017256448 * column9_row192
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column20_row145 - column20_row17 * (column9_row192 - (column9_row193 + column9_row193))
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column20_row17 * (column9_row193 - 8 * column9_row196)) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column20_row17 -
        (column9_row251 - (column9_row252 + column9_row252)) * (
            column9_row196 - (column9_row197 + column9_row197)
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column9_row251 - (column9_row252 + column9_row252)) * (
            column9_row197 - 18014398509481984 * column9_row251
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash2__ec_subset_sum__bit_0 * (pedersen__hash2__ec_subset_sum__bit_0 - 1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/bit_extraction_end.
    tempvar value = (column9_row0) / domain10;
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/zeros_tail.
    tempvar value = (column9_row0) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash2__ec_subset_sum__bit_0 * (column8_row0 - global_values.pedersen__points__y) -
        column15_row0 * (column7_row0 - global_values.pedersen__points__x)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/add_points/x.
    tempvar value = (
        column15_row0 * column15_row0 -
        pedersen__hash2__ec_subset_sum__bit_0 * (
            column7_row0 + global_values.pedersen__points__x + column7_row1
        )
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash2__ec_subset_sum__bit_0 * (column8_row0 + column8_row1) -
        column15_row0 * (column7_row0 - column7_row1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash2__ec_subset_sum__bit_neg_0 * (column7_row1 - column7_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    // Constraint: pedersen/hash2/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash2__ec_subset_sum__bit_neg_0 * (column8_row1 - column8_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    // Constraint: pedersen/hash2/copy_point/x.
    tempvar value = (column7_row256 - column7_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    // Constraint: pedersen/hash2/copy_point/y.
    tempvar value = (column8_row256 - column8_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    // Constraint: pedersen/hash2/init/x.
    tempvar value = (column7_row0 - global_values.pedersen__shift_point.x) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    // Constraint: pedersen/hash2/init/y.
    tempvar value = (column8_row0 - global_values.pedersen__shift_point.y) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column20_row209 * (column12_row0 - (column12_row1 + column12_row1))) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column20_row209 * (
            column12_row1 -
            3138550867693340381917894711603833208051177722232017256448 * column12_row192
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column20_row209 - column20_row81 * (column12_row192 - (column12_row193 + column12_row193))
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column20_row81 * (column12_row193 - 8 * column12_row196)) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column20_row81 -
        (column12_row251 - (column12_row252 + column12_row252)) * (
            column12_row196 - (column12_row197 + column12_row197)
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column12_row251 - (column12_row252 + column12_row252)) * (
            column12_row197 - 18014398509481984 * column12_row251
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash3__ec_subset_sum__bit_0 * (pedersen__hash3__ec_subset_sum__bit_0 - 1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/bit_extraction_end.
    tempvar value = (column12_row0) / domain10;
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/zeros_tail.
    tempvar value = (column12_row0) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash3__ec_subset_sum__bit_0 * (
            column11_row0 - global_values.pedersen__points__y
        ) -
        column16_row0 * (column10_row0 - global_values.pedersen__points__x)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/add_points/x.
    tempvar value = (
        column16_row0 * column16_row0 -
        pedersen__hash3__ec_subset_sum__bit_0 * (
            column10_row0 + global_values.pedersen__points__x + column10_row1
        )
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash3__ec_subset_sum__bit_0 * (column11_row0 + column11_row1) -
        column16_row0 * (column10_row0 - column10_row1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash3__ec_subset_sum__bit_neg_0 * (column10_row1 - column10_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    // Constraint: pedersen/hash3/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash3__ec_subset_sum__bit_neg_0 * (column11_row1 - column11_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    // Constraint: pedersen/hash3/copy_point/x.
    tempvar value = (column10_row256 - column10_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    // Constraint: pedersen/hash3/copy_point/y.
    tempvar value = (column11_row256 - column11_row255) * domain11 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    // Constraint: pedersen/hash3/init/x.
    tempvar value = (column10_row0 - global_values.pedersen__shift_point.x) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    // Constraint: pedersen/hash3/init/y.
    tempvar value = (column11_row0 - global_values.pedersen__shift_point.y) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    // Constraint: pedersen/input0_value0.
    tempvar value = (column17_row7 - column3_row0) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    // Constraint: pedersen/input0_value1.
    tempvar value = (column17_row135 - column6_row0) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    // Constraint: pedersen/input0_value2.
    tempvar value = (column17_row263 - column9_row0) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    // Constraint: pedersen/input0_value3.
    tempvar value = (column17_row391 - column12_row0) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    // Constraint: pedersen/input0_addr.
    tempvar value = (column17_row134 - (column17_row38 + 1)) * domain23 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    // Constraint: pedersen/init_addr.
    tempvar value = (column17_row6 - global_values.initial_pedersen_addr) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    // Constraint: pedersen/input1_value0.
    tempvar value = (column17_row71 - column3_row256) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    // Constraint: pedersen/input1_value1.
    tempvar value = (column17_row199 - column6_row256) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    // Constraint: pedersen/input1_value2.
    tempvar value = (column17_row327 - column9_row256) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    // Constraint: pedersen/input1_value3.
    tempvar value = (column17_row455 - column12_row256) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    // Constraint: pedersen/input1_addr.
    tempvar value = (column17_row70 - (column17_row6 + 1)) / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    // Constraint: pedersen/output_value0.
    tempvar value = (column17_row39 - column1_row511) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    // Constraint: pedersen/output_value1.
    tempvar value = (column17_row167 - column4_row511) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    // Constraint: pedersen/output_value2.
    tempvar value = (column17_row295 - column7_row511) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    // Constraint: pedersen/output_value3.
    tempvar value = (column17_row423 - column10_row511) / domain12;
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

    // Constraint: pedersen/output_addr.
    tempvar value = (column17_row38 - (column17_row70 + 1)) / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[134] * value;

    // Constraint: rc_builtin/value.
    tempvar value = (rc_builtin__value7_0 - column17_row103) / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[135] * value;

    // Constraint: rc_builtin/addr_step.
    tempvar value = (column17_row230 - (column17_row102 + 1)) * domain23 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[136] * value;

    // Constraint: rc_builtin/init_addr.
    tempvar value = (column17_row102 - global_values.initial_rc_addr) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[137] * value;

    // Constraint: ecdsa/signature0/doubling_key/slope.
    tempvar value = (
        ecdsa__signature0__doubling_key__x_squared +
        ecdsa__signature0__doubling_key__x_squared +
        ecdsa__signature0__doubling_key__x_squared +
        global_values.ecdsa__sig_config.alpha -
        (column19_row15 + column19_row15) * column20_row12
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[138] * value;

    // Constraint: ecdsa/signature0/doubling_key/x.
    tempvar value = (
        column20_row12 * column20_row12 - (column19_row7 + column19_row7 + column19_row23)
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[139] * value;

    // Constraint: ecdsa/signature0/doubling_key/y.
    tempvar value = (
        column19_row15 + column19_row31 - column20_row12 * (column19_row7 - column19_row23)
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[140] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/booleanity_test.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            ecdsa__signature0__exponentiate_generator__bit_0 - 1
        )
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[141] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/bit_extraction_end.
    tempvar value = (column20_row14) / domain17;
    tempvar total_sum = total_sum + constraint_coefficients[142] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/zeros_tail.
    tempvar value = (column20_row14) / domain16;
    tempvar total_sum = total_sum + constraint_coefficients[143] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/slope.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            column20_row22 - global_values.ecdsa__generator_points__y
        ) -
        column20_row30 * (column20_row6 - global_values.ecdsa__generator_points__x)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[144] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/x.
    tempvar value = (
        column20_row30 * column20_row30 -
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            column20_row6 + global_values.ecdsa__generator_points__x + column20_row38
        )
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[145] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (column20_row22 + column20_row54) -
        column20_row30 * (column20_row6 - column20_row38)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[146] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/x_diff_inv.
    tempvar value = (
        column20_row1 * (column20_row6 - global_values.ecdsa__generator_points__x) - 1
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[147] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/copy_point/x.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_neg_0 * (column20_row38 - column20_row6)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[148] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/copy_point/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_neg_0 * (column20_row54 - column20_row22)
    ) * domain16 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[149] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/booleanity_test.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (
            ecdsa__signature0__exponentiate_key__bit_0 - 1
        )
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[150] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/bit_extraction_end.
    tempvar value = (column20_row4) / domain14;
    tempvar total_sum = total_sum + constraint_coefficients[151] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/zeros_tail.
    tempvar value = (column20_row4) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[152] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/slope.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (column20_row8 - column19_row15) -
        column20_row2 * (column20_row0 - column19_row7)
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[153] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/x.
    tempvar value = (
        column20_row2 * column20_row2 -
        ecdsa__signature0__exponentiate_key__bit_0 * (
            column20_row0 + column19_row7 + column20_row16
        )
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[154] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (column20_row8 + column20_row24) -
        column20_row2 * (column20_row0 - column20_row16)
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[155] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/x_diff_inv.
    tempvar value = (column20_row10 * (column20_row0 - column19_row7) - 1) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[156] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/copy_point/x.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_neg_0 * (column20_row16 - column20_row0)
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[157] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/copy_point/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_neg_0 * (column20_row24 - column20_row8)
    ) * domain13 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[158] * value;

    // Constraint: ecdsa/signature0/init_gen/x.
    tempvar value = (column20_row6 - global_values.ecdsa__sig_config.shift_point.x) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[159] * value;

    // Constraint: ecdsa/signature0/init_gen/y.
    tempvar value = (column20_row22 + global_values.ecdsa__sig_config.shift_point.y) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[160] * value;

    // Constraint: ecdsa/signature0/init_key/x.
    tempvar value = (column20_row0 - global_values.ecdsa__sig_config.shift_point.x) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[161] * value;

    // Constraint: ecdsa/signature0/init_key/y.
    tempvar value = (column20_row8 - global_values.ecdsa__sig_config.shift_point.y) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[162] * value;

    // Constraint: ecdsa/signature0/add_results/slope.
    tempvar value = (
        column20_row8182 -
        (column20_row4088 + column20_row8190 * (column20_row8166 - column20_row4080))
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[163] * value;

    // Constraint: ecdsa/signature0/add_results/x.
    tempvar value = (
        column20_row8190 * column20_row8190 -
        (column20_row8166 + column20_row4080 + column19_row4103)
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[164] * value;

    // Constraint: ecdsa/signature0/add_results/y.
    tempvar value = (
        column20_row8182 +
        column19_row4111 -
        column20_row8190 * (column20_row8166 - column19_row4103)
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[165] * value;

    // Constraint: ecdsa/signature0/add_results/x_diff_inv.
    tempvar value = (column20_row8161 * (column20_row8166 - column20_row4080) - 1) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[166] * value;

    // Constraint: ecdsa/signature0/extract_r/slope.
    tempvar value = (
        column20_row8184 +
        global_values.ecdsa__sig_config.shift_point.y -
        column20_row4082 * (column20_row8176 - global_values.ecdsa__sig_config.shift_point.x)
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[167] * value;

    // Constraint: ecdsa/signature0/extract_r/x.
    tempvar value = (
        column20_row4082 * column20_row4082 -
        (column20_row8176 + global_values.ecdsa__sig_config.shift_point.x + column20_row4)
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[168] * value;

    // Constraint: ecdsa/signature0/extract_r/x_diff_inv.
    tempvar value = (
        column20_row8178 * (column20_row8176 - global_values.ecdsa__sig_config.shift_point.x) - 1
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[169] * value;

    // Constraint: ecdsa/signature0/z_nonzero.
    tempvar value = (column20_row14 * column20_row4090 - 1) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[170] * value;

    // Constraint: ecdsa/signature0/r_and_w_nonzero.
    tempvar value = (column20_row4 * column20_row4092 - 1) / domain15;
    tempvar total_sum = total_sum + constraint_coefficients[171] * value;

    // Constraint: ecdsa/signature0/q_on_curve/x_squared.
    tempvar value = (column20_row8186 - column19_row7 * column19_row7) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[172] * value;

    // Constraint: ecdsa/signature0/q_on_curve/on_curve.
    tempvar value = (
        column19_row15 * column19_row15 -
        (
            column19_row7 * column20_row8186 +
            global_values.ecdsa__sig_config.alpha * column19_row7 +
            global_values.ecdsa__sig_config.beta
        )
    ) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[173] * value;

    // Constraint: ecdsa/init_addr.
    tempvar value = (column17_row22 - global_values.initial_ecdsa_addr) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[174] * value;

    // Constraint: ecdsa/message_addr.
    tempvar value = (column17_row4118 - (column17_row22 + 1)) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[175] * value;

    // Constraint: ecdsa/pubkey_addr.
    tempvar value = (column17_row8214 - (column17_row4118 + 1)) * domain24 / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[176] * value;

    // Constraint: ecdsa/message_value0.
    tempvar value = (column17_row4119 - column20_row14) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[177] * value;

    // Constraint: ecdsa/pubkey_value0.
    tempvar value = (column17_row23 - column19_row7) / domain18;
    tempvar total_sum = total_sum + constraint_coefficients[178] * value;

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
    local pow18 = pow3 * pow17;
    local pow19 = pow2 * pow18;
    local pow20 = pow1 * pow19;
    local pow21 = pow1 * pow20;
    local pow22 = pow1 * pow21;
    local pow23 = pow3 * pow22;
    local pow24 = pow2 * pow23;
    local pow25 = pow1 * pow24;
    local pow26 = pow7 * pow25;
    local pow27 = pow1 * pow26;
    local pow28 = pow5 * pow27;
    local pow29 = pow2 * pow28;
    local pow30 = pow8 * pow29;
    local pow31 = pow6 * pow30;
    local pow32 = pow10 * pow31;
    local pow33 = pow1 * pow32;
    local pow34 = pow5 * pow33;
    local pow35 = pow5 * pow34;
    local pow36 = pow11 * pow35;
    local pow37 = pow10 * pow36;
    local pow38 = pow1 * pow37;
    local pow39 = pow5 * pow38;
    local pow40 = pow16 * pow39;
    local pow41 = pow10 * pow40;
    local pow42 = pow1 * pow41;
    local pow43 = pow10 * pow42;
    local pow44 = pow19 * pow43;
    local pow45 = pow22 * pow44;
    local pow46 = pow1 * pow45;
    local pow47 = pow3 * pow46;
    local pow48 = pow1 * pow47;
    local pow49 = pow2 * pow48;
    local pow50 = pow10 * pow49;
    local pow51 = pow25 * pow49;
    local pow52 = pow30 * pow48;
    local pow53 = pow1 * pow52;
    local pow54 = pow3 * pow53;
    local pow55 = pow1 * pow54;
    local pow56 = pow7 * pow55;
    local pow57 = pow27 * pow55;
    local pow58 = pow33 * pow55;
    local pow59 = pow42 * pow55;
    local pow60 = pow44 * pow55;
    local pow61 = pow45 * pow56;
    local pow62 = pow54 * pow55;
    let (local pow63) = pow(trace_generator, 4080);
    local pow64 = pow2 * pow63;
    local pow65 = pow6 * pow64;
    local pow66 = pow2 * pow65;
    local pow67 = pow2 * pow66;
    local pow68 = pow11 * pow67;
    local pow69 = pow8 * pow68;
    local pow70 = pow7 * pow69;
    local pow71 = pow1 * pow70;
    let (local pow72) = pow(trace_generator, 8161);
    local pow73 = pow5 * pow72;
    local pow74 = pow10 * pow73;
    local pow75 = pow2 * pow74;
    local pow76 = pow4 * pow75;
    local pow77 = pow2 * pow76;
    local pow78 = pow2 * pow77;
    local pow79 = pow4 * pow78;
    local pow80 = pow21 * pow79;

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
    tempvar column10 = column_values[10];
    tempvar column11 = column_values[11];
    tempvar column12 = column_values[12];
    tempvar column13 = column_values[13];
    tempvar column14 = column_values[14];
    tempvar column15 = column_values[15];
    tempvar column16 = column_values[16];
    tempvar column17 = column_values[17];
    tempvar column18 = column_values[18];
    tempvar column19 = column_values[19];
    tempvar column20 = column_values[20];
    tempvar column21 = column_values[21];

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

    tempvar value = (column1 - oods_values[18]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    tempvar value = (column1 - oods_values[19]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    tempvar value = (column1 - oods_values[20]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    tempvar value = (column2 - oods_values[21]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[21] * value;

    tempvar value = (column2 - oods_values[22]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    tempvar value = (column2 - oods_values[23]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    tempvar value = (column2 - oods_values[24]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[24] * value;

    tempvar value = (column3 - oods_values[25]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    tempvar value = (column3 - oods_values[26]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    tempvar value = (column3 - oods_values[27]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    tempvar value = (column3 - oods_values[28]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    tempvar value = (column3 - oods_values[29]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    tempvar value = (column3 - oods_values[30]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    tempvar value = (column3 - oods_values[31]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    tempvar value = (column3 - oods_values[32]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    tempvar value = (column3 - oods_values[33]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    tempvar value = (column4 - oods_values[34]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    tempvar value = (column4 - oods_values[35]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    tempvar value = (column4 - oods_values[36]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    tempvar value = (column4 - oods_values[37]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    tempvar value = (column4 - oods_values[38]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    tempvar value = (column5 - oods_values[39]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    tempvar value = (column5 - oods_values[40]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    tempvar value = (column5 - oods_values[41]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    tempvar value = (column5 - oods_values[42]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    tempvar value = (column6 - oods_values[43]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    tempvar value = (column6 - oods_values[44]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    tempvar value = (column6 - oods_values[45]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    tempvar value = (column6 - oods_values[46]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    tempvar value = (column6 - oods_values[47]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    tempvar value = (column6 - oods_values[48]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    tempvar value = (column6 - oods_values[49]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    tempvar value = (column6 - oods_values[50]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    tempvar value = (column6 - oods_values[51]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    tempvar value = (column7 - oods_values[52]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    tempvar value = (column7 - oods_values[53]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    tempvar value = (column7 - oods_values[54]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    tempvar value = (column7 - oods_values[55]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    tempvar value = (column7 - oods_values[56]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    tempvar value = (column8 - oods_values[57]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    tempvar value = (column8 - oods_values[58]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    tempvar value = (column8 - oods_values[59]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    tempvar value = (column8 - oods_values[60]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    tempvar value = (column9 - oods_values[61]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    tempvar value = (column9 - oods_values[62]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    tempvar value = (column9 - oods_values[63]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    tempvar value = (column9 - oods_values[64]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    tempvar value = (column9 - oods_values[65]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    tempvar value = (column9 - oods_values[66]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    tempvar value = (column9 - oods_values[67]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    tempvar value = (column9 - oods_values[68]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    tempvar value = (column9 - oods_values[69]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    tempvar value = (column10 - oods_values[70]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    tempvar value = (column10 - oods_values[71]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    tempvar value = (column10 - oods_values[72]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    tempvar value = (column10 - oods_values[73]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    tempvar value = (column10 - oods_values[74]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    tempvar value = (column11 - oods_values[75]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    tempvar value = (column11 - oods_values[76]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    tempvar value = (column11 - oods_values[77]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    tempvar value = (column11 - oods_values[78]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    tempvar value = (column12 - oods_values[79]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    tempvar value = (column12 - oods_values[80]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    tempvar value = (column12 - oods_values[81]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    tempvar value = (column12 - oods_values[82]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    tempvar value = (column12 - oods_values[83]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    tempvar value = (column12 - oods_values[84]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    tempvar value = (column12 - oods_values[85]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    tempvar value = (column12 - oods_values[86]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    tempvar value = (column12 - oods_values[87]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    tempvar value = (column13 - oods_values[88]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    tempvar value = (column13 - oods_values[89]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    tempvar value = (column14 - oods_values[90]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    tempvar value = (column14 - oods_values[91]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    tempvar value = (column15 - oods_values[92]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    tempvar value = (column15 - oods_values[93]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    tempvar value = (column16 - oods_values[94]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    tempvar value = (column16 - oods_values[95]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    tempvar value = (column17 - oods_values[96]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    tempvar value = (column17 - oods_values[97]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    tempvar value = (column17 - oods_values[98]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    tempvar value = (column17 - oods_values[99]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    tempvar value = (column17 - oods_values[100]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    tempvar value = (column17 - oods_values[101]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    tempvar value = (column17 - oods_values[102]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    tempvar value = (column17 - oods_values[103]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    tempvar value = (column17 - oods_values[104]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    tempvar value = (column17 - oods_values[105]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    tempvar value = (column17 - oods_values[106]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    tempvar value = (column17 - oods_values[107]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    tempvar value = (column17 - oods_values[108]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    tempvar value = (column17 - oods_values[109]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    tempvar value = (column17 - oods_values[110]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    tempvar value = (column17 - oods_values[111]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    tempvar value = (column17 - oods_values[112]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    tempvar value = (column17 - oods_values[113]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    tempvar value = (column17 - oods_values[114]) / (point - pow33 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    tempvar value = (column17 - oods_values[115]) / (point - pow37 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    tempvar value = (column17 - oods_values[116]) / (point - pow38 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    tempvar value = (column17 - oods_values[117]) / (point - pow41 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    tempvar value = (column17 - oods_values[118]) / (point - pow42 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    tempvar value = (column17 - oods_values[119]) / (point - pow44 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    tempvar value = (column17 - oods_values[120]) / (point - pow49 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    tempvar value = (column17 - oods_values[121]) / (point - pow51 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    tempvar value = (column17 - oods_values[122]) / (point - pow56 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    tempvar value = (column17 - oods_values[123]) / (point - pow57 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    tempvar value = (column17 - oods_values[124]) / (point - pow58 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    tempvar value = (column17 - oods_values[125]) / (point - pow59 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    tempvar value = (column17 - oods_values[126]) / (point - pow60 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    tempvar value = (column17 - oods_values[127]) / (point - pow61 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    tempvar value = (column17 - oods_values[128]) / (point - pow70 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    tempvar value = (column17 - oods_values[129]) / (point - pow71 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    tempvar value = (column17 - oods_values[130]) / (point - pow80 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    tempvar value = (column18 - oods_values[131]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    tempvar value = (column18 - oods_values[132]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    tempvar value = (column18 - oods_values[133]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

    tempvar value = (column18 - oods_values[134]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[134] * value;

    tempvar value = (column19 - oods_values[135]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[135] * value;

    tempvar value = (column19 - oods_values[136]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[136] * value;

    tempvar value = (column19 - oods_values[137]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[137] * value;

    tempvar value = (column19 - oods_values[138]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[138] * value;

    tempvar value = (column19 - oods_values[139]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[139] * value;

    tempvar value = (column19 - oods_values[140]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[140] * value;

    tempvar value = (column19 - oods_values[141]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[141] * value;

    tempvar value = (column19 - oods_values[142]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[142] * value;

    tempvar value = (column19 - oods_values[143]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[143] * value;

    tempvar value = (column19 - oods_values[144]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[144] * value;

    tempvar value = (column19 - oods_values[145]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[145] * value;

    tempvar value = (column19 - oods_values[146]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[146] * value;

    tempvar value = (column19 - oods_values[147]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[147] * value;

    tempvar value = (column19 - oods_values[148]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[148] * value;

    tempvar value = (column19 - oods_values[149]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[149] * value;

    tempvar value = (column19 - oods_values[150]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[150] * value;

    tempvar value = (column19 - oods_values[151]) / (point - pow22 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[151] * value;

    tempvar value = (column19 - oods_values[152]) / (point - pow23 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[152] * value;

    tempvar value = (column19 - oods_values[153]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[153] * value;

    tempvar value = (column19 - oods_values[154]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[154] * value;

    tempvar value = (column19 - oods_values[155]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[155] * value;

    tempvar value = (column19 - oods_values[156]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[156] * value;

    tempvar value = (column19 - oods_values[157]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[157] * value;

    tempvar value = (column19 - oods_values[158]) / (point - pow39 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[158] * value;

    tempvar value = (column19 - oods_values[159]) / (point - pow40 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[159] * value;

    tempvar value = (column19 - oods_values[160]) / (point - pow68 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[160] * value;

    tempvar value = (column19 - oods_values[161]) / (point - pow69 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[161] * value;

    tempvar value = (column20 - oods_values[162]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[162] * value;

    tempvar value = (column20 - oods_values[163]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[163] * value;

    tempvar value = (column20 - oods_values[164]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[164] * value;

    tempvar value = (column20 - oods_values[165]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[165] * value;

    tempvar value = (column20 - oods_values[166]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[166] * value;

    tempvar value = (column20 - oods_values[167]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[167] * value;

    tempvar value = (column20 - oods_values[168]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[168] * value;

    tempvar value = (column20 - oods_values[169]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[169] * value;

    tempvar value = (column20 - oods_values[170]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[170] * value;

    tempvar value = (column20 - oods_values[171]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[171] * value;

    tempvar value = (column20 - oods_values[172]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[172] * value;

    tempvar value = (column20 - oods_values[173]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[173] * value;

    tempvar value = (column20 - oods_values[174]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[174] * value;

    tempvar value = (column20 - oods_values[175]) / (point - pow21 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[175] * value;

    tempvar value = (column20 - oods_values[176]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[176] * value;

    tempvar value = (column20 - oods_values[177]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[177] * value;

    tempvar value = (column20 - oods_values[178]) / (point - pow29 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[178] * value;

    tempvar value = (column20 - oods_values[179]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[179] * value;

    tempvar value = (column20 - oods_values[180]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[180] * value;

    tempvar value = (column20 - oods_values[181]) / (point - pow43 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[181] * value;

    tempvar value = (column20 - oods_values[182]) / (point - pow50 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[182] * value;

    tempvar value = (column20 - oods_values[183]) / (point - pow63 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[183] * value;

    tempvar value = (column20 - oods_values[184]) / (point - pow64 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[184] * value;

    tempvar value = (column20 - oods_values[185]) / (point - pow65 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[185] * value;

    tempvar value = (column20 - oods_values[186]) / (point - pow66 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[186] * value;

    tempvar value = (column20 - oods_values[187]) / (point - pow67 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[187] * value;

    tempvar value = (column20 - oods_values[188]) / (point - pow72 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[188] * value;

    tempvar value = (column20 - oods_values[189]) / (point - pow73 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[189] * value;

    tempvar value = (column20 - oods_values[190]) / (point - pow74 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[190] * value;

    tempvar value = (column20 - oods_values[191]) / (point - pow75 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[191] * value;

    tempvar value = (column20 - oods_values[192]) / (point - pow76 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[192] * value;

    tempvar value = (column20 - oods_values[193]) / (point - pow77 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[193] * value;

    tempvar value = (column20 - oods_values[194]) / (point - pow78 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[194] * value;

    tempvar value = (column20 - oods_values[195]) / (point - pow79 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[195] * value;

    tempvar value = (column21 - oods_values[196]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[196] * value;

    tempvar value = (column21 - oods_values[197]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[197] * value;

    tempvar value = (column21 - oods_values[198]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[198] * value;

    tempvar value = (column21 - oods_values[199]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[199] * value;

    // Sum the OODS boundary constraints on the composition polynomials.
    let (oods_point_to_deg) = pow(oods_point, CONSTRAINT_DEGREE);

    tempvar value = (column_values[22] - oods_values[200]) / (point - oods_point_to_deg);
    tempvar total_sum = total_sum + constraint_coefficients[200] * value;

    tempvar value = (column_values[23] - oods_values[201]) / (point - oods_point_to_deg);
    tempvar total_sum = total_sum + constraint_coefficients[201] * value;

    static_assert 202 == MASK_SIZE + CONSTRAINT_DEGREE;
    return (res=total_sum);
}
