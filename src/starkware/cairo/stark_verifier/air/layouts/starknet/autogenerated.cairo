from starkware.cairo.stark_verifier.air.layouts.starknet.global_values import GlobalValues
from starkware.cairo.common.math import safe_div, safe_mult
from starkware.cairo.common.pow import pow

const N_DYNAMIC_PARAMS = 0;
const N_CONSTRAINTS = 198;
const MASK_SIZE = 271;
const CPU_COMPONENT_STEP = 1;
const CPU_COMPONENT_HEIGHT = 16;
const PUBLIC_MEMORY_STEP = 8;
const HAS_DILUTED_POOL = 1;
const DILUTED_SPACING = 4;
const DILUTED_N_BITS = 16;
const PEDERSEN_BUILTIN_RATIO = 32;
const PEDERSEN_BUILTIN_ROW_RATIO = 512;
const PEDERSEN_BUILTIN_REPETITIONS = 1;
const RANGE_CHECK_BUILTIN_RATIO = 16;
const RANGE_CHECK_BUILTIN_ROW_RATIO = 256;
const RANGE_CHECK_N_PARTS = 8;
const ECDSA_BUILTIN_RATIO = 2048;
const ECDSA_BUILTIN_ROW_RATIO = 32768;
const ECDSA_BUILTIN_REPETITIONS = 1;
const ECDSA_ELEMENT_BITS = 251;
const ECDSA_ELEMENT_HEIGHT = 256;
const BITWISE__RATIO = 64;
const BITWISE__ROW_RATIO = 1024;
const BITWISE__TOTAL_N_BITS = 251;
const EC_OP_BUILTIN_RATIO = 1024;
const EC_OP_BUILTIN_ROW_RATIO = 16384;
const EC_OP_SCALAR_HEIGHT = 256;
const EC_OP_N_BITS = 252;
const POSEIDON__RATIO = 32;
const POSEIDON__ROW_RATIO = 512;
const POSEIDON__M = 3;
const POSEIDON__ROUNDS_FULL = 8;
const POSEIDON__ROUNDS_PARTIAL = 83;
const HAS_OUTPUT_BUILTIN = 1;
const HAS_PEDERSEN_BUILTIN = 1;
const HAS_RANGE_CHECK_BUILTIN = 1;
const HAS_ECDSA_BUILTIN = 1;
const HAS_BITWISE_BUILTIN = 1;
const HAS_EC_OP_BUILTIN = 1;
const HAS_KECCAK_BUILTIN = 0;
const HAS_POSEIDON_BUILTIN = 1;
const HAS_RANGE_CHECK96_BUILTIN = 0;
const HAS_ADD_MOD_BUILTIN = 0;
const HAS_MUL_MOD_BUILTIN = 0;
const LAYOUT_CODE = 0x737461726b6e6574;
const CONSTRAINT_DEGREE = 2;
const LOG_CPU_COMPONENT_HEIGHT = 4;
const NUM_COLUMNS_FIRST = 9;
const NUM_COLUMNS_SECOND = 1;
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
    let (local pow0) = pow(point, (safe_div(global_values.trace_length, 32768)));
    local pow1 = pow0 * pow0;  // pow(point, (safe_div(global_values.trace_length, 16384))).
    let (local pow2) = pow(point, (safe_div(global_values.trace_length, 1024)));
    local pow3 = pow2 * pow2;  // pow(point, (safe_div(global_values.trace_length, 512))).
    local pow4 = pow3 * pow3;  // pow(point, (safe_div(global_values.trace_length, 256))).
    local pow5 = pow4 * pow4;  // pow(point, (safe_div(global_values.trace_length, 128))).
    local pow6 = pow5 * pow5;  // pow(point, (safe_div(global_values.trace_length, 64))).
    let (local pow7) = pow(point, (safe_div(global_values.trace_length, 16)));
    local pow8 = pow7 * pow7;  // pow(point, (safe_div(global_values.trace_length, 8))).
    local pow9 = pow8 * pow8;  // pow(point, (safe_div(global_values.trace_length, 4))).
    local pow10 = pow9 * pow9;  // pow(point, (safe_div(global_values.trace_length, 2))).
    local pow11 = pow10 * pow10;  // pow(point, global_values.trace_length).
    let (local pow12) = pow(trace_generator, global_values.trace_length - 16384);
    let (local pow13) = pow(trace_generator, global_values.trace_length - 1024);
    let (local pow14) = pow(trace_generator, global_values.trace_length - 32768);
    let (local pow15) = pow(trace_generator, global_values.trace_length - 256);
    let (local pow16) = pow(trace_generator, global_values.trace_length - 512);
    let (local pow17) = pow(trace_generator, global_values.trace_length - 8);
    let (local pow18) = pow(trace_generator, global_values.trace_length - 4);
    let (local pow19) = pow(trace_generator, global_values.trace_length - 2);
    let (local pow20) = pow(trace_generator, global_values.trace_length - 16);
    let (local pow21) = pow(
        trace_generator, (safe_div((safe_mult(251, global_values.trace_length)), 256))
    );
    let (local pow22) = pow(trace_generator, (safe_div(global_values.trace_length, 64)));
    local pow23 = pow22 * pow22;  // pow(trace_generator, (safe_div(global_values.trace_length, 32))).
    local pow24 = pow22 * pow23;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 64))).
    local pow25 = pow22 * pow24;  // pow(trace_generator, (safe_div(global_values.trace_length, 16))).
    local pow26 = pow22 * pow25;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 64))).
    local pow27 = pow22 * pow26;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 32))).
    local pow28 = pow22 * pow27;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 64))).
    local pow29 = pow22 * pow28;  // pow(trace_generator, (safe_div(global_values.trace_length, 8))).
    local pow30 = pow22 * pow29;  // pow(trace_generator, (safe_div((safe_mult(9, global_values.trace_length)), 64))).
    local pow31 = pow22 * pow30;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 32))).
    local pow32 = pow22 * pow31;  // pow(trace_generator, (safe_div((safe_mult(11, global_values.trace_length)), 64))).
    local pow33 = pow22 * pow32;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 16))).
    local pow34 = pow22 * pow33;  // pow(trace_generator, (safe_div((safe_mult(13, global_values.trace_length)), 64))).
    local pow35 = pow22 * pow34;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 32))).
    local pow36 = pow22 * pow35;  // pow(trace_generator, (safe_div((safe_mult(15, global_values.trace_length)), 64))).
    let (local pow37) = pow(trace_generator, (safe_div(global_values.trace_length, 2)));
    local pow38 = pow27 * pow37;  // pow(trace_generator, (safe_div((safe_mult(19, global_values.trace_length)), 32))).
    local pow39 = pow23 * pow38;  // pow(trace_generator, (safe_div((safe_mult(5, global_values.trace_length)), 8))).
    local pow40 = pow23 * pow39;  // pow(trace_generator, (safe_div((safe_mult(21, global_values.trace_length)), 32))).
    local pow41 = pow23 * pow40;  // pow(trace_generator, (safe_div((safe_mult(11, global_values.trace_length)), 16))).
    local pow42 = pow23 * pow41;  // pow(trace_generator, (safe_div((safe_mult(23, global_values.trace_length)), 32))).
    local pow43 = pow23 * pow42;  // pow(trace_generator, (safe_div((safe_mult(3, global_values.trace_length)), 4))).
    local pow44 = pow23 * pow43;  // pow(trace_generator, (safe_div((safe_mult(25, global_values.trace_length)), 32))).
    local pow45 = pow23 * pow44;  // pow(trace_generator, (safe_div((safe_mult(13, global_values.trace_length)), 16))).
    local pow46 = pow23 * pow45;  // pow(trace_generator, (safe_div((safe_mult(27, global_values.trace_length)), 32))).
    local pow47 = pow23 * pow46;  // pow(trace_generator, (safe_div((safe_mult(7, global_values.trace_length)), 8))).
    local pow48 = pow23 * pow47;  // pow(trace_generator, (safe_div((safe_mult(29, global_values.trace_length)), 32))).
    local pow49 = pow21 * pow22;  // pow(trace_generator, (safe_div((safe_mult(255, global_values.trace_length)), 256))).
    local pow50 = pow23 * pow48;  // pow(trace_generator, (safe_div((safe_mult(15, global_values.trace_length)), 16))).
    local pow51 = pow22 * pow50;  // pow(trace_generator, (safe_div((safe_mult(61, global_values.trace_length)), 64))).
    local pow52 = pow22 * pow51;  // pow(trace_generator, (safe_div((safe_mult(31, global_values.trace_length)), 32))).
    local pow53 = pow22 * pow52;  // pow(trace_generator, (safe_div((safe_mult(63, global_values.trace_length)), 64))).

    // Compute domains.
    tempvar domain0 = pow11 - 1;
    tempvar domain1 = pow10 - 1;
    tempvar domain2 = pow9 - 1;
    tempvar domain3 = pow8 - 1;
    tempvar domain4 = pow7 - pow50;
    tempvar domain5 = pow7 - 1;
    tempvar domain6 = pow6 - 1;
    tempvar domain7 = pow5 - 1;
    tempvar domain8 = pow4 - 1;
    tempvar domain9 = pow4 - pow49;
    tempvar domain10 = pow4 - pow53;
    tempvar domain11 = pow4 - pow43;
    tempvar domain12 = pow3 - pow37;
    tempvar domain13 = pow3 - 1;
    tempvar domain14 = pow3 - pow52;
    tempvar temp = pow3 - pow41;
    tempvar temp = temp * (pow3 - pow42);
    tempvar temp = temp * (pow3 - pow43);
    tempvar temp = temp * (pow3 - pow44);
    tempvar temp = temp * (pow3 - pow45);
    tempvar temp = temp * (pow3 - pow46);
    tempvar temp = temp * (pow3 - pow47);
    tempvar temp = temp * (pow3 - pow48);
    tempvar temp = temp * (pow3 - pow50);
    tempvar domain15 = temp * (domain14);
    tempvar temp = pow3 - pow51;
    tempvar temp = temp * (pow3 - pow53);
    tempvar domain16 = temp * (domain14);
    tempvar temp = pow3 - pow38;
    tempvar temp = temp * (pow3 - pow39);
    tempvar temp = temp * (pow3 - pow40);
    tempvar domain17 = temp * (domain15);
    tempvar domain18 = pow2 - pow43;
    tempvar domain19 = pow2 - 1;
    tempvar temp = pow2 - pow22;
    tempvar temp = temp * (pow2 - pow23);
    tempvar temp = temp * (pow2 - pow24);
    tempvar temp = temp * (pow2 - pow25);
    tempvar temp = temp * (pow2 - pow26);
    tempvar temp = temp * (pow2 - pow27);
    tempvar temp = temp * (pow2 - pow28);
    tempvar temp = temp * (pow2 - pow29);
    tempvar temp = temp * (pow2 - pow30);
    tempvar temp = temp * (pow2 - pow31);
    tempvar temp = temp * (pow2 - pow32);
    tempvar temp = temp * (pow2 - pow33);
    tempvar temp = temp * (pow2 - pow34);
    tempvar temp = temp * (pow2 - pow35);
    tempvar temp = temp * (pow2 - pow36);
    tempvar domain20 = temp * (domain19);
    tempvar domain21 = pow1 - pow49;
    tempvar domain22 = pow1 - pow21;
    tempvar domain23 = pow1 - 1;
    tempvar domain24 = pow1 - pow53;
    tempvar domain25 = pow0 - pow49;
    tempvar domain26 = pow0 - pow21;
    tempvar domain27 = pow0 - 1;
    tempvar domain28 = point - pow20;
    tempvar domain29 = point - 1;
    tempvar domain30 = point - pow19;
    tempvar domain31 = point - pow18;
    tempvar domain32 = point - pow17;
    tempvar domain33 = point - pow16;
    tempvar domain34 = point - pow15;
    tempvar domain35 = point - pow14;
    tempvar domain36 = point - pow13;
    tempvar domain37 = point - pow12;

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
    tempvar column4_row255 = mask_values[35];
    tempvar column5_row0 = mask_values[36];
    tempvar column5_row1 = mask_values[37];
    tempvar column5_row2 = mask_values[38];
    tempvar column5_row3 = mask_values[39];
    tempvar column5_row4 = mask_values[40];
    tempvar column5_row5 = mask_values[41];
    tempvar column5_row6 = mask_values[42];
    tempvar column5_row7 = mask_values[43];
    tempvar column5_row8 = mask_values[44];
    tempvar column5_row9 = mask_values[45];
    tempvar column5_row12 = mask_values[46];
    tempvar column5_row13 = mask_values[47];
    tempvar column5_row16 = mask_values[48];
    tempvar column5_row38 = mask_values[49];
    tempvar column5_row39 = mask_values[50];
    tempvar column5_row70 = mask_values[51];
    tempvar column5_row71 = mask_values[52];
    tempvar column5_row102 = mask_values[53];
    tempvar column5_row103 = mask_values[54];
    tempvar column5_row134 = mask_values[55];
    tempvar column5_row135 = mask_values[56];
    tempvar column5_row166 = mask_values[57];
    tempvar column5_row167 = mask_values[58];
    tempvar column5_row198 = mask_values[59];
    tempvar column5_row199 = mask_values[60];
    tempvar column5_row262 = mask_values[61];
    tempvar column5_row263 = mask_values[62];
    tempvar column5_row294 = mask_values[63];
    tempvar column5_row295 = mask_values[64];
    tempvar column5_row326 = mask_values[65];
    tempvar column5_row358 = mask_values[66];
    tempvar column5_row359 = mask_values[67];
    tempvar column5_row390 = mask_values[68];
    tempvar column5_row391 = mask_values[69];
    tempvar column5_row422 = mask_values[70];
    tempvar column5_row423 = mask_values[71];
    tempvar column5_row454 = mask_values[72];
    tempvar column5_row518 = mask_values[73];
    tempvar column5_row711 = mask_values[74];
    tempvar column5_row902 = mask_values[75];
    tempvar column5_row903 = mask_values[76];
    tempvar column5_row966 = mask_values[77];
    tempvar column5_row967 = mask_values[78];
    tempvar column5_row1222 = mask_values[79];
    tempvar column5_row2438 = mask_values[80];
    tempvar column5_row2439 = mask_values[81];
    tempvar column5_row4486 = mask_values[82];
    tempvar column5_row4487 = mask_values[83];
    tempvar column5_row6534 = mask_values[84];
    tempvar column5_row6535 = mask_values[85];
    tempvar column5_row8582 = mask_values[86];
    tempvar column5_row8583 = mask_values[87];
    tempvar column5_row10630 = mask_values[88];
    tempvar column5_row10631 = mask_values[89];
    tempvar column5_row12678 = mask_values[90];
    tempvar column5_row12679 = mask_values[91];
    tempvar column5_row14726 = mask_values[92];
    tempvar column5_row14727 = mask_values[93];
    tempvar column5_row16774 = mask_values[94];
    tempvar column5_row16775 = mask_values[95];
    tempvar column5_row24966 = mask_values[96];
    tempvar column5_row33158 = mask_values[97];
    tempvar column6_row0 = mask_values[98];
    tempvar column6_row1 = mask_values[99];
    tempvar column6_row2 = mask_values[100];
    tempvar column6_row3 = mask_values[101];
    tempvar column7_row0 = mask_values[102];
    tempvar column7_row1 = mask_values[103];
    tempvar column7_row2 = mask_values[104];
    tempvar column7_row3 = mask_values[105];
    tempvar column7_row4 = mask_values[106];
    tempvar column7_row5 = mask_values[107];
    tempvar column7_row6 = mask_values[108];
    tempvar column7_row7 = mask_values[109];
    tempvar column7_row8 = mask_values[110];
    tempvar column7_row9 = mask_values[111];
    tempvar column7_row11 = mask_values[112];
    tempvar column7_row12 = mask_values[113];
    tempvar column7_row13 = mask_values[114];
    tempvar column7_row15 = mask_values[115];
    tempvar column7_row17 = mask_values[116];
    tempvar column7_row19 = mask_values[117];
    tempvar column7_row23 = mask_values[118];
    tempvar column7_row27 = mask_values[119];
    tempvar column7_row33 = mask_values[120];
    tempvar column7_row44 = mask_values[121];
    tempvar column7_row49 = mask_values[122];
    tempvar column7_row65 = mask_values[123];
    tempvar column7_row76 = mask_values[124];
    tempvar column7_row81 = mask_values[125];
    tempvar column7_row97 = mask_values[126];
    tempvar column7_row108 = mask_values[127];
    tempvar column7_row113 = mask_values[128];
    tempvar column7_row129 = mask_values[129];
    tempvar column7_row140 = mask_values[130];
    tempvar column7_row145 = mask_values[131];
    tempvar column7_row161 = mask_values[132];
    tempvar column7_row172 = mask_values[133];
    tempvar column7_row177 = mask_values[134];
    tempvar column7_row193 = mask_values[135];
    tempvar column7_row204 = mask_values[136];
    tempvar column7_row209 = mask_values[137];
    tempvar column7_row225 = mask_values[138];
    tempvar column7_row236 = mask_values[139];
    tempvar column7_row241 = mask_values[140];
    tempvar column7_row257 = mask_values[141];
    tempvar column7_row265 = mask_values[142];
    tempvar column7_row491 = mask_values[143];
    tempvar column7_row499 = mask_values[144];
    tempvar column7_row507 = mask_values[145];
    tempvar column7_row513 = mask_values[146];
    tempvar column7_row521 = mask_values[147];
    tempvar column7_row705 = mask_values[148];
    tempvar column7_row721 = mask_values[149];
    tempvar column7_row737 = mask_values[150];
    tempvar column7_row753 = mask_values[151];
    tempvar column7_row769 = mask_values[152];
    tempvar column7_row777 = mask_values[153];
    tempvar column7_row961 = mask_values[154];
    tempvar column7_row977 = mask_values[155];
    tempvar column7_row993 = mask_values[156];
    tempvar column7_row1009 = mask_values[157];
    tempvar column8_row0 = mask_values[158];
    tempvar column8_row1 = mask_values[159];
    tempvar column8_row2 = mask_values[160];
    tempvar column8_row3 = mask_values[161];
    tempvar column8_row4 = mask_values[162];
    tempvar column8_row5 = mask_values[163];
    tempvar column8_row6 = mask_values[164];
    tempvar column8_row7 = mask_values[165];
    tempvar column8_row8 = mask_values[166];
    tempvar column8_row9 = mask_values[167];
    tempvar column8_row10 = mask_values[168];
    tempvar column8_row11 = mask_values[169];
    tempvar column8_row12 = mask_values[170];
    tempvar column8_row13 = mask_values[171];
    tempvar column8_row14 = mask_values[172];
    tempvar column8_row16 = mask_values[173];
    tempvar column8_row17 = mask_values[174];
    tempvar column8_row19 = mask_values[175];
    tempvar column8_row21 = mask_values[176];
    tempvar column8_row22 = mask_values[177];
    tempvar column8_row24 = mask_values[178];
    tempvar column8_row25 = mask_values[179];
    tempvar column8_row27 = mask_values[180];
    tempvar column8_row29 = mask_values[181];
    tempvar column8_row30 = mask_values[182];
    tempvar column8_row33 = mask_values[183];
    tempvar column8_row35 = mask_values[184];
    tempvar column8_row37 = mask_values[185];
    tempvar column8_row38 = mask_values[186];
    tempvar column8_row41 = mask_values[187];
    tempvar column8_row43 = mask_values[188];
    tempvar column8_row45 = mask_values[189];
    tempvar column8_row46 = mask_values[190];
    tempvar column8_row49 = mask_values[191];
    tempvar column8_row51 = mask_values[192];
    tempvar column8_row53 = mask_values[193];
    tempvar column8_row54 = mask_values[194];
    tempvar column8_row57 = mask_values[195];
    tempvar column8_row59 = mask_values[196];
    tempvar column8_row61 = mask_values[197];
    tempvar column8_row65 = mask_values[198];
    tempvar column8_row69 = mask_values[199];
    tempvar column8_row71 = mask_values[200];
    tempvar column8_row73 = mask_values[201];
    tempvar column8_row77 = mask_values[202];
    tempvar column8_row81 = mask_values[203];
    tempvar column8_row85 = mask_values[204];
    tempvar column8_row89 = mask_values[205];
    tempvar column8_row91 = mask_values[206];
    tempvar column8_row97 = mask_values[207];
    tempvar column8_row101 = mask_values[208];
    tempvar column8_row105 = mask_values[209];
    tempvar column8_row109 = mask_values[210];
    tempvar column8_row113 = mask_values[211];
    tempvar column8_row117 = mask_values[212];
    tempvar column8_row123 = mask_values[213];
    tempvar column8_row155 = mask_values[214];
    tempvar column8_row187 = mask_values[215];
    tempvar column8_row195 = mask_values[216];
    tempvar column8_row205 = mask_values[217];
    tempvar column8_row219 = mask_values[218];
    tempvar column8_row221 = mask_values[219];
    tempvar column8_row237 = mask_values[220];
    tempvar column8_row245 = mask_values[221];
    tempvar column8_row253 = mask_values[222];
    tempvar column8_row269 = mask_values[223];
    tempvar column8_row301 = mask_values[224];
    tempvar column8_row309 = mask_values[225];
    tempvar column8_row310 = mask_values[226];
    tempvar column8_row318 = mask_values[227];
    tempvar column8_row326 = mask_values[228];
    tempvar column8_row334 = mask_values[229];
    tempvar column8_row342 = mask_values[230];
    tempvar column8_row350 = mask_values[231];
    tempvar column8_row451 = mask_values[232];
    tempvar column8_row461 = mask_values[233];
    tempvar column8_row477 = mask_values[234];
    tempvar column8_row493 = mask_values[235];
    tempvar column8_row501 = mask_values[236];
    tempvar column8_row509 = mask_values[237];
    tempvar column8_row12309 = mask_values[238];
    tempvar column8_row12373 = mask_values[239];
    tempvar column8_row12565 = mask_values[240];
    tempvar column8_row12629 = mask_values[241];
    tempvar column8_row16085 = mask_values[242];
    tempvar column8_row16149 = mask_values[243];
    tempvar column8_row16325 = mask_values[244];
    tempvar column8_row16331 = mask_values[245];
    tempvar column8_row16337 = mask_values[246];
    tempvar column8_row16339 = mask_values[247];
    tempvar column8_row16355 = mask_values[248];
    tempvar column8_row16357 = mask_values[249];
    tempvar column8_row16363 = mask_values[250];
    tempvar column8_row16369 = mask_values[251];
    tempvar column8_row16371 = mask_values[252];
    tempvar column8_row16385 = mask_values[253];
    tempvar column8_row16417 = mask_values[254];
    tempvar column8_row32647 = mask_values[255];
    tempvar column8_row32667 = mask_values[256];
    tempvar column8_row32715 = mask_values[257];
    tempvar column8_row32721 = mask_values[258];
    tempvar column8_row32731 = mask_values[259];
    tempvar column8_row32747 = mask_values[260];
    tempvar column8_row32753 = mask_values[261];
    tempvar column8_row32763 = mask_values[262];
    tempvar column9_inter1_row0 = mask_values[263];
    tempvar column9_inter1_row1 = mask_values[264];
    tempvar column9_inter1_row2 = mask_values[265];
    tempvar column9_inter1_row3 = mask_values[266];
    tempvar column9_inter1_row5 = mask_values[267];
    tempvar column9_inter1_row7 = mask_values[268];
    tempvar column9_inter1_row11 = mask_values[269];
    tempvar column9_inter1_row15 = mask_values[270];

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
    tempvar npc_reg_0 = column5_row0 + cpu__decode__opcode_range_check__bit_2 + 1;
    tempvar cpu__decode__opcode_range_check__bit_10 = column0_row10 - (
        column0_row11 + column0_row11
    );
    tempvar cpu__decode__opcode_range_check__bit_11 = column0_row11 - (
        column0_row12 + column0_row12
    );
    tempvar cpu__decode__opcode_range_check__bit_14 = column0_row14 - (
        column0_row15 + column0_row15
    );
    tempvar memory__address_diff_0 = column6_row2 - column6_row0;
    tempvar range_check16__diff_0 = column7_row6 - column7_row2;
    tempvar pedersen__hash0__ec_subset_sum__bit_0 = column3_row0 - (column3_row1 + column3_row1);
    tempvar pedersen__hash0__ec_subset_sum__bit_neg_0 = 1 - pedersen__hash0__ec_subset_sum__bit_0;
    tempvar range_check_builtin__value0_0 = column7_row12;
    tempvar range_check_builtin__value1_0 = range_check_builtin__value0_0 *
        global_values.offset_size + column7_row44;
    tempvar range_check_builtin__value2_0 = range_check_builtin__value1_0 *
        global_values.offset_size + column7_row76;
    tempvar range_check_builtin__value3_0 = range_check_builtin__value2_0 *
        global_values.offset_size + column7_row108;
    tempvar range_check_builtin__value4_0 = range_check_builtin__value3_0 *
        global_values.offset_size + column7_row140;
    tempvar range_check_builtin__value5_0 = range_check_builtin__value4_0 *
        global_values.offset_size + column7_row172;
    tempvar range_check_builtin__value6_0 = range_check_builtin__value5_0 *
        global_values.offset_size + column7_row204;
    tempvar range_check_builtin__value7_0 = range_check_builtin__value6_0 *
        global_values.offset_size + column7_row236;
    tempvar ecdsa__signature0__doubling_key__x_squared = column8_row1 * column8_row1;
    tempvar ecdsa__signature0__exponentiate_generator__bit_0 = column8_row59 - (
        column8_row187 + column8_row187
    );
    tempvar ecdsa__signature0__exponentiate_generator__bit_neg_0 = 1 -
        ecdsa__signature0__exponentiate_generator__bit_0;
    tempvar ecdsa__signature0__exponentiate_key__bit_0 = column8_row9 - (
        column8_row73 + column8_row73
    );
    tempvar ecdsa__signature0__exponentiate_key__bit_neg_0 = 1 -
        ecdsa__signature0__exponentiate_key__bit_0;
    tempvar bitwise__sum_var_0_0 = column7_row1 + column7_row17 * 2 + column7_row33 * 4 +
        column7_row49 * 8 + column7_row65 * 18446744073709551616 + column7_row81 *
        36893488147419103232 + column7_row97 * 73786976294838206464 + column7_row113 *
        147573952589676412928;
    tempvar bitwise__sum_var_8_0 = column7_row129 * 340282366920938463463374607431768211456 +
        column7_row145 * 680564733841876926926749214863536422912 + column7_row161 *
        1361129467683753853853498429727072845824 + column7_row177 *
        2722258935367507707706996859454145691648 + column7_row193 *
        6277101735386680763835789423207666416102355444464034512896 + column7_row209 *
        12554203470773361527671578846415332832204710888928069025792 + column7_row225 *
        25108406941546723055343157692830665664409421777856138051584 + column7_row241 *
        50216813883093446110686315385661331328818843555712276103168;
    tempvar ec_op__doubling_q__x_squared_0 = column8_row41 * column8_row41;
    tempvar ec_op__ec_subset_sum__bit_0 = column8_row21 - (column8_row85 + column8_row85);
    tempvar ec_op__ec_subset_sum__bit_neg_0 = 1 - ec_op__ec_subset_sum__bit_0;
    tempvar poseidon__poseidon__full_rounds_state0_cubed_0 = column8_row53 * column8_row29;
    tempvar poseidon__poseidon__full_rounds_state1_cubed_0 = column8_row13 * column8_row61;
    tempvar poseidon__poseidon__full_rounds_state2_cubed_0 = column8_row45 * column8_row3;
    tempvar poseidon__poseidon__full_rounds_state0_cubed_7 = column8_row501 * column8_row477;
    tempvar poseidon__poseidon__full_rounds_state1_cubed_7 = column8_row461 * column8_row509;
    tempvar poseidon__poseidon__full_rounds_state2_cubed_7 = column8_row493 * column8_row451;
    tempvar poseidon__poseidon__full_rounds_state0_cubed_3 = column8_row245 * column8_row221;
    tempvar poseidon__poseidon__full_rounds_state1_cubed_3 = column8_row205 * column8_row253;
    tempvar poseidon__poseidon__full_rounds_state2_cubed_3 = column8_row237 * column8_row195;
    tempvar poseidon__poseidon__partial_rounds_state0_cubed_0 = column7_row3 * column7_row7;
    tempvar poseidon__poseidon__partial_rounds_state0_cubed_1 = column7_row11 * column7_row15;
    tempvar poseidon__poseidon__partial_rounds_state0_cubed_2 = column7_row19 * column7_row23;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_0 = column8_row6 * column8_row14;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_1 = column8_row22 * column8_row30;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_2 = column8_row38 * column8_row46;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_19 = column8_row310 * column8_row318;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_20 = column8_row326 * column8_row334;
    tempvar poseidon__poseidon__partial_rounds_state1_cubed_21 = column8_row342 * column8_row350;

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
        column5_row1 -
        (
            (
                (column0_row0 * global_values.offset_size + column7_row4) *
                global_values.offset_size +
                column7_row8
            ) * global_values.offset_size +
            column7_row0
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
        column5_row8 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_0 * column8_row8 +
            (1 - cpu__decode__opcode_range_check__bit_0) * column8_row0 +
            column7_row0
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    // Constraint: cpu/operands/mem0_addr.
    tempvar value = (
        column5_row4 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_1 * column8_row8 +
            (1 - cpu__decode__opcode_range_check__bit_1) * column8_row0 +
            column7_row8
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    // Constraint: cpu/operands/mem1_addr.
    tempvar value = (
        column5_row12 +
        global_values.half_offset_size -
        (
            cpu__decode__opcode_range_check__bit_2 * column5_row0 +
            cpu__decode__opcode_range_check__bit_4 * column8_row0 +
            cpu__decode__opcode_range_check__bit_3 * column8_row8 +
            cpu__decode__flag_op1_base_op0_0 * column5_row5 +
            column7_row4
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    // Constraint: cpu/operands/ops_mul.
    tempvar value = (column8_row4 - column5_row5 * column5_row13) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    // Constraint: cpu/operands/res.
    tempvar value = (
        (1 - cpu__decode__opcode_range_check__bit_9) * column8_row12 -
        (
            cpu__decode__opcode_range_check__bit_5 * (column5_row5 + column5_row13) +
            cpu__decode__opcode_range_check__bit_6 * column8_row4 +
            cpu__decode__flag_res_op1_0 * column5_row13
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    // Constraint: cpu/update_registers/update_pc/tmp0.
    tempvar value = (column8_row2 - cpu__decode__opcode_range_check__bit_9 * column5_row9) *
        domain28 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    // Constraint: cpu/update_registers/update_pc/tmp1.
    tempvar value = (column8_row10 - column8_row2 * column8_row12) * domain28 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_negative.
    tempvar value = (
        (1 - cpu__decode__opcode_range_check__bit_9) * column5_row16 +
        column8_row2 * (column5_row16 - (column5_row0 + column5_row13)) -
        (
            cpu__decode__flag_pc_update_regular_0 * npc_reg_0 +
            cpu__decode__opcode_range_check__bit_7 * column8_row12 +
            cpu__decode__opcode_range_check__bit_8 * (column5_row0 + column8_row12)
        )
    ) * domain28 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    // Constraint: cpu/update_registers/update_pc/pc_cond_positive.
    tempvar value = (
        (column8_row10 - cpu__decode__opcode_range_check__bit_9) * (column5_row16 - npc_reg_0)
    ) * domain28 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    // Constraint: cpu/update_registers/update_ap/ap_update.
    tempvar value = (
        column8_row16 -
        (
            column8_row0 +
            cpu__decode__opcode_range_check__bit_10 * column8_row12 +
            cpu__decode__opcode_range_check__bit_11 +
            cpu__decode__opcode_range_check__bit_12 * 2
        )
    ) * domain28 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    // Constraint: cpu/update_registers/update_fp/fp_update.
    tempvar value = (
        column8_row24 -
        (
            cpu__decode__fp_update_regular_0 * column8_row8 +
            cpu__decode__opcode_range_check__bit_13 * column5_row9 +
            cpu__decode__opcode_range_check__bit_12 * (column8_row0 + 2)
        )
    ) * domain28 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    // Constraint: cpu/opcodes/call/push_fp.
    tempvar value = (cpu__decode__opcode_range_check__bit_12 * (column5_row9 - column8_row8)) /
        domain5;
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    // Constraint: cpu/opcodes/call/push_pc.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (
            column5_row5 - (column5_row0 + cpu__decode__opcode_range_check__bit_2 + 1)
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    // Constraint: cpu/opcodes/call/off0.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (column7_row0 - global_values.half_offset_size)
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    // Constraint: cpu/opcodes/call/off1.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_12 * (
            column7_row8 - (global_values.half_offset_size + 1)
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
            column7_row0 + 2 - global_values.half_offset_size
        )
    ) / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    // Constraint: cpu/opcodes/ret/off2.
    tempvar value = (
        cpu__decode__opcode_range_check__bit_13 * (
            column7_row4 + 1 - global_values.half_offset_size
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
    tempvar value = (cpu__decode__opcode_range_check__bit_14 * (column5_row9 - column8_row12)) /
        domain5;
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    // Constraint: initial_ap.
    tempvar value = (column8_row0 - global_values.initial_ap) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    // Constraint: initial_fp.
    tempvar value = (column8_row8 - global_values.initial_ap) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    // Constraint: initial_pc.
    tempvar value = (column5_row0 - global_values.initial_pc) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    // Constraint: final_ap.
    tempvar value = (column8_row0 - global_values.final_ap) / domain28;
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    // Constraint: final_fp.
    tempvar value = (column8_row8 - global_values.initial_ap) / domain28;
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    // Constraint: final_pc.
    tempvar value = (column5_row0 - global_values.final_pc) / domain28;
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    // Constraint: memory/multi_column_perm/perm/init0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column6_row0 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column6_row1
            )
        ) * column9_inter1_row0 +
        column5_row0 +
        global_values.memory__multi_column_perm__hash_interaction_elm0 * column5_row1 -
        global_values.memory__multi_column_perm__perm__interaction_elm
    ) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    // Constraint: memory/multi_column_perm/perm/step0.
    tempvar value = (
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column6_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column6_row3
            )
        ) * column9_inter1_row2 -
        (
            global_values.memory__multi_column_perm__perm__interaction_elm -
            (
                column5_row2 +
                global_values.memory__multi_column_perm__hash_interaction_elm0 * column5_row3
            )
        ) * column9_inter1_row0
    ) * domain30 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    // Constraint: memory/multi_column_perm/perm/last.
    tempvar value = (
        column9_inter1_row0 - global_values.memory__multi_column_perm__perm__public_memory_prod
    ) / domain30;
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    // Constraint: memory/diff_is_bit.
    tempvar value = (memory__address_diff_0 * memory__address_diff_0 - memory__address_diff_0) *
        domain30 / domain1;
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    // Constraint: memory/is_func.
    tempvar value = ((memory__address_diff_0 - 1) * (column6_row1 - column6_row3)) * domain30 /
        domain1;
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    // Constraint: memory/initial_addr.
    tempvar value = (column6_row0 - 1) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    // Constraint: public_memory_addr_zero.
    tempvar value = (column5_row2) / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    // Constraint: public_memory_value_zero.
    tempvar value = (column5_row3) / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    // Constraint: range_check16/perm/init0.
    tempvar value = (
        (global_values.range_check16__perm__interaction_elm - column7_row2) * column9_inter1_row1 +
        column7_row0 -
        global_values.range_check16__perm__interaction_elm
    ) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    // Constraint: range_check16/perm/step0.
    tempvar value = (
        (global_values.range_check16__perm__interaction_elm - column7_row6) * column9_inter1_row5 -
        (global_values.range_check16__perm__interaction_elm - column7_row4) * column9_inter1_row1
    ) * domain31 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    // Constraint: range_check16/perm/last.
    tempvar value = (column9_inter1_row1 - global_values.range_check16__perm__public_memory_prod) /
        domain31;
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    // Constraint: range_check16/diff_is_bit.
    tempvar value = (range_check16__diff_0 * range_check16__diff_0 - range_check16__diff_0) *
        domain31 / domain2;
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    // Constraint: range_check16/minimum.
    tempvar value = (column7_row2 - global_values.range_check_min) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    // Constraint: range_check16/maximum.
    tempvar value = (column7_row2 - global_values.range_check_max) / domain31;
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    // Constraint: diluted_check/permutation/init0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column7_row5) *
        column9_inter1_row7 +
        column7_row1 -
        global_values.diluted_check__permutation__interaction_elm
    ) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    // Constraint: diluted_check/permutation/step0.
    tempvar value = (
        (global_values.diluted_check__permutation__interaction_elm - column7_row13) *
        column9_inter1_row15 -
        (global_values.diluted_check__permutation__interaction_elm - column7_row9) *
        column9_inter1_row7
    ) * domain32 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    // Constraint: diluted_check/permutation/last.
    tempvar value = (
        column9_inter1_row7 - global_values.diluted_check__permutation__public_memory_prod
    ) / domain32;
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    // Constraint: diluted_check/init.
    tempvar value = (column9_inter1_row3 - 1) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    // Constraint: diluted_check/first_element.
    tempvar value = (column7_row5 - global_values.diluted_check__first_elm) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    // Constraint: diluted_check/step.
    tempvar value = (
        column9_inter1_row11 -
        (
            column9_inter1_row3 * (
                1 + global_values.diluted_check__interaction_z * (column7_row13 - column7_row5)
            ) +
            global_values.diluted_check__interaction_alpha * (column7_row13 - column7_row5) * (
                column7_row13 - column7_row5
            )
        )
    ) * domain32 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    // Constraint: diluted_check/last.
    tempvar value = (column9_inter1_row3 - global_values.diluted_check__final_cum_val) / domain32;
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column8_row71 * (column3_row0 - (column3_row1 + column3_row1))) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column8_row71 * (
            column3_row1 -
            3138550867693340381917894711603833208051177722232017256448 * column3_row192
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column8_row71 - column4_row255 * (column3_row192 - (column3_row193 + column3_row193))
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column4_row255 * (column3_row193 - 8 * column3_row196)) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column4_row255 -
        (column3_row251 - (column3_row252 + column3_row252)) * (
            column3_row196 - (column3_row197 + column3_row197)
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column3_row251 - (column3_row252 + column3_row252)) * (
            column3_row197 - 18014398509481984 * column3_row251
        )
    ) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/booleanity_test.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (pedersen__hash0__ec_subset_sum__bit_0 - 1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/bit_extraction_end.
    tempvar value = (column3_row0) / domain10;
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/zeros_tail.
    tempvar value = (column3_row0) / domain9;
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/slope.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column2_row0 - global_values.pedersen__points__y) -
        column4_row0 * (column1_row0 - global_values.pedersen__points__x)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/x.
    tempvar value = (
        column4_row0 * column4_row0 -
        pedersen__hash0__ec_subset_sum__bit_0 * (
            column1_row0 + global_values.pedersen__points__x + column1_row1
        )
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/add_points/y.
    tempvar value = (
        pedersen__hash0__ec_subset_sum__bit_0 * (column2_row0 + column2_row1) -
        column4_row0 * (column1_row0 - column1_row1)
    ) * domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/x.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column1_row1 - column1_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    // Constraint: pedersen/hash0/ec_subset_sum/copy_point/y.
    tempvar value = (pedersen__hash0__ec_subset_sum__bit_neg_0 * (column2_row1 - column2_row0)) *
        domain9 / domain0;
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    // Constraint: pedersen/hash0/copy_point/x.
    tempvar value = (column1_row256 - column1_row255) * domain12 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    // Constraint: pedersen/hash0/copy_point/y.
    tempvar value = (column2_row256 - column2_row255) * domain12 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    // Constraint: pedersen/hash0/init/x.
    tempvar value = (column1_row0 - global_values.pedersen__shift_point.x) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    // Constraint: pedersen/hash0/init/y.
    tempvar value = (column2_row0 - global_values.pedersen__shift_point.y) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    // Constraint: pedersen/input0_value0.
    tempvar value = (column5_row7 - column3_row0) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    // Constraint: pedersen/input0_addr.
    tempvar value = (column5_row518 - (column5_row134 + 1)) * domain33 / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    // Constraint: pedersen/init_addr.
    tempvar value = (column5_row6 - global_values.initial_pedersen_addr) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    // Constraint: pedersen/input1_value0.
    tempvar value = (column5_row263 - column3_row256) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    // Constraint: pedersen/input1_addr.
    tempvar value = (column5_row262 - (column5_row6 + 1)) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    // Constraint: pedersen/output_value0.
    tempvar value = (column5_row135 - column1_row511) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    // Constraint: pedersen/output_addr.
    tempvar value = (column5_row134 - (column5_row262 + 1)) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    // Constraint: range_check_builtin/value.
    tempvar value = (range_check_builtin__value7_0 - column5_row71) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    // Constraint: range_check_builtin/addr_step.
    tempvar value = (column5_row326 - (column5_row70 + 1)) * domain34 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    // Constraint: range_check_builtin/init_addr.
    tempvar value = (column5_row70 - global_values.initial_range_check_addr) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    // Constraint: ecdsa/signature0/doubling_key/slope.
    tempvar value = (
        ecdsa__signature0__doubling_key__x_squared +
        ecdsa__signature0__doubling_key__x_squared +
        ecdsa__signature0__doubling_key__x_squared +
        global_values.ecdsa__sig_config.alpha -
        (column8_row33 + column8_row33) * column8_row35
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    // Constraint: ecdsa/signature0/doubling_key/x.
    tempvar value = (
        column8_row35 * column8_row35 - (column8_row1 + column8_row1 + column8_row65)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    // Constraint: ecdsa/signature0/doubling_key/y.
    tempvar value = (
        column8_row33 + column8_row97 - column8_row35 * (column8_row1 - column8_row65)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/booleanity_test.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            ecdsa__signature0__exponentiate_generator__bit_0 - 1
        )
    ) * domain25 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/bit_extraction_end.
    tempvar value = (column8_row59) / domain26;
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/zeros_tail.
    tempvar value = (column8_row59) / domain25;
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/slope.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            column8_row91 - global_values.ecdsa__generator_points__y
        ) -
        column8_row123 * (column8_row27 - global_values.ecdsa__generator_points__x)
    ) * domain25 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/x.
    tempvar value = (
        column8_row123 * column8_row123 -
        ecdsa__signature0__exponentiate_generator__bit_0 * (
            column8_row27 + global_values.ecdsa__generator_points__x + column8_row155
        )
    ) * domain25 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_0 * (column8_row91 + column8_row219) -
        column8_row123 * (column8_row27 - column8_row155)
    ) * domain25 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/add_points/x_diff_inv.
    tempvar value = (
        column8_row7 * (column8_row27 - global_values.ecdsa__generator_points__x) - 1
    ) * domain25 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/copy_point/x.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_neg_0 * (column8_row155 - column8_row27)
    ) * domain25 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    // Constraint: ecdsa/signature0/exponentiate_generator/copy_point/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_generator__bit_neg_0 * (column8_row219 - column8_row91)
    ) * domain25 / domain7;
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/booleanity_test.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (
            ecdsa__signature0__exponentiate_key__bit_0 - 1
        )
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/bit_extraction_end.
    tempvar value = (column8_row9) / domain22;
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/zeros_tail.
    tempvar value = (column8_row9) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/slope.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (column8_row49 - column8_row33) -
        column8_row19 * (column8_row17 - column8_row1)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/x.
    tempvar value = (
        column8_row19 * column8_row19 -
        ecdsa__signature0__exponentiate_key__bit_0 * (column8_row17 + column8_row1 + column8_row81)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_0 * (column8_row49 + column8_row113) -
        column8_row19 * (column8_row17 - column8_row81)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/add_points/x_diff_inv.
    tempvar value = (column8_row51 * (column8_row17 - column8_row1) - 1) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/copy_point/x.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_neg_0 * (column8_row81 - column8_row17)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    // Constraint: ecdsa/signature0/exponentiate_key/copy_point/y.
    tempvar value = (
        ecdsa__signature0__exponentiate_key__bit_neg_0 * (column8_row113 - column8_row49)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    // Constraint: ecdsa/signature0/init_gen/x.
    tempvar value = (column8_row27 - global_values.ecdsa__sig_config.shift_point.x) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    // Constraint: ecdsa/signature0/init_gen/y.
    tempvar value = (column8_row91 + global_values.ecdsa__sig_config.shift_point.y) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    // Constraint: ecdsa/signature0/init_key/x.
    tempvar value = (column8_row17 - global_values.ecdsa__sig_config.shift_point.x) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    // Constraint: ecdsa/signature0/init_key/y.
    tempvar value = (column8_row49 - global_values.ecdsa__sig_config.shift_point.y) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    // Constraint: ecdsa/signature0/add_results/slope.
    tempvar value = (
        column8_row32731 -
        (column8_row16369 + column8_row32763 * (column8_row32667 - column8_row16337))
    ) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    // Constraint: ecdsa/signature0/add_results/x.
    tempvar value = (
        column8_row32763 * column8_row32763 -
        (column8_row32667 + column8_row16337 + column8_row16385)
    ) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    // Constraint: ecdsa/signature0/add_results/y.
    tempvar value = (
        column8_row32731 +
        column8_row16417 -
        column8_row32763 * (column8_row32667 - column8_row16385)
    ) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    // Constraint: ecdsa/signature0/add_results/x_diff_inv.
    tempvar value = (column8_row32647 * (column8_row32667 - column8_row16337) - 1) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    // Constraint: ecdsa/signature0/extract_r/slope.
    tempvar value = (
        column8_row32753 +
        global_values.ecdsa__sig_config.shift_point.y -
        column8_row16331 * (column8_row32721 - global_values.ecdsa__sig_config.shift_point.x)
    ) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    // Constraint: ecdsa/signature0/extract_r/x.
    tempvar value = (
        column8_row16331 * column8_row16331 -
        (column8_row32721 + global_values.ecdsa__sig_config.shift_point.x + column8_row9)
    ) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    // Constraint: ecdsa/signature0/extract_r/x_diff_inv.
    tempvar value = (
        column8_row32715 * (column8_row32721 - global_values.ecdsa__sig_config.shift_point.x) - 1
    ) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    // Constraint: ecdsa/signature0/z_nonzero.
    tempvar value = (column8_row59 * column8_row16363 - 1) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    // Constraint: ecdsa/signature0/r_and_w_nonzero.
    tempvar value = (column8_row9 * column8_row16355 - 1) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    // Constraint: ecdsa/signature0/q_on_curve/x_squared.
    tempvar value = (column8_row32747 - column8_row1 * column8_row1) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    // Constraint: ecdsa/signature0/q_on_curve/on_curve.
    tempvar value = (
        column8_row33 * column8_row33 -
        (
            column8_row1 * column8_row32747 +
            global_values.ecdsa__sig_config.alpha * column8_row1 +
            global_values.ecdsa__sig_config.beta
        )
    ) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    // Constraint: ecdsa/init_addr.
    tempvar value = (column5_row390 - global_values.initial_ecdsa_addr) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    // Constraint: ecdsa/message_addr.
    tempvar value = (column5_row16774 - (column5_row390 + 1)) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    // Constraint: ecdsa/pubkey_addr.
    tempvar value = (column5_row33158 - (column5_row16774 + 1)) * domain35 / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    // Constraint: ecdsa/message_value0.
    tempvar value = (column5_row16775 - column8_row59) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    // Constraint: ecdsa/pubkey_value0.
    tempvar value = (column5_row391 - column8_row1) / domain27;
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    // Constraint: bitwise/init_var_pool_addr.
    tempvar value = (column5_row198 - global_values.initial_bitwise_addr) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    // Constraint: bitwise/step_var_pool_addr.
    tempvar value = (column5_row454 - (column5_row198 + 1)) * domain18 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    // Constraint: bitwise/x_or_y_addr.
    tempvar value = (column5_row902 - (column5_row966 + 1)) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    // Constraint: bitwise/next_var_pool_addr.
    tempvar value = (column5_row1222 - (column5_row902 + 1)) * domain36 / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    // Constraint: bitwise/partition.
    tempvar value = (bitwise__sum_var_0_0 + bitwise__sum_var_8_0 - column5_row199) / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    // Constraint: bitwise/or_is_and_plus_xor.
    tempvar value = (column5_row903 - (column5_row711 + column5_row967)) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    // Constraint: bitwise/addition_is_xor_with_and.
    tempvar value = (
        column7_row1 + column7_row257 - (column7_row769 + column7_row513 + column7_row513)
    ) / domain20;
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    // Constraint: bitwise/unique_unpacking192.
    tempvar value = ((column7_row705 + column7_row961) * 16 - column7_row9) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    // Constraint: bitwise/unique_unpacking193.
    tempvar value = ((column7_row721 + column7_row977) * 16 - column7_row521) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    // Constraint: bitwise/unique_unpacking194.
    tempvar value = ((column7_row737 + column7_row993) * 16 - column7_row265) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    // Constraint: bitwise/unique_unpacking195.
    tempvar value = ((column7_row753 + column7_row1009) * 256 - column7_row777) / domain19;
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

    // Constraint: ec_op/init_addr.
    tempvar value = (column5_row8582 - global_values.initial_ec_op_addr) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[134] * value;

    // Constraint: ec_op/p_x_addr.
    tempvar value = (column5_row24966 - (column5_row8582 + 7)) * domain37 / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[135] * value;

    // Constraint: ec_op/p_y_addr.
    tempvar value = (column5_row4486 - (column5_row8582 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[136] * value;

    // Constraint: ec_op/q_x_addr.
    tempvar value = (column5_row12678 - (column5_row4486 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[137] * value;

    // Constraint: ec_op/q_y_addr.
    tempvar value = (column5_row2438 - (column5_row12678 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[138] * value;

    // Constraint: ec_op/m_addr.
    tempvar value = (column5_row10630 - (column5_row2438 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[139] * value;

    // Constraint: ec_op/r_x_addr.
    tempvar value = (column5_row6534 - (column5_row10630 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[140] * value;

    // Constraint: ec_op/r_y_addr.
    tempvar value = (column5_row14726 - (column5_row6534 + 1)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[141] * value;

    // Constraint: ec_op/doubling_q/slope.
    tempvar value = (
        ec_op__doubling_q__x_squared_0 +
        ec_op__doubling_q__x_squared_0 +
        ec_op__doubling_q__x_squared_0 +
        global_values.ec_op__curve_config.alpha -
        (column8_row25 + column8_row25) * column8_row57
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[142] * value;

    // Constraint: ec_op/doubling_q/x.
    tempvar value = (
        column8_row57 * column8_row57 - (column8_row41 + column8_row41 + column8_row105)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[143] * value;

    // Constraint: ec_op/doubling_q/y.
    tempvar value = (
        column8_row25 + column8_row89 - column8_row57 * (column8_row41 - column8_row105)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[144] * value;

    // Constraint: ec_op/get_q_x.
    tempvar value = (column5_row12679 - column8_row41) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[145] * value;

    // Constraint: ec_op/get_q_y.
    tempvar value = (column5_row2439 - column8_row25) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[146] * value;

    // Constraint: ec_op/ec_subset_sum/bit_unpacking/last_one_is_zero.
    tempvar value = (column8_row16371 * (column8_row21 - (column8_row85 + column8_row85))) /
        domain23;
    tempvar total_sum = total_sum + constraint_coefficients[147] * value;

    // Constraint: ec_op/ec_subset_sum/bit_unpacking/zeroes_between_ones0.
    tempvar value = (
        column8_row16371 * (
            column8_row85 -
            3138550867693340381917894711603833208051177722232017256448 * column8_row12309
        )
    ) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[148] * value;

    // Constraint: ec_op/ec_subset_sum/bit_unpacking/cumulative_bit192.
    tempvar value = (
        column8_row16371 -
        column8_row16339 * (column8_row12309 - (column8_row12373 + column8_row12373))
    ) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[149] * value;

    // Constraint: ec_op/ec_subset_sum/bit_unpacking/zeroes_between_ones192.
    tempvar value = (column8_row16339 * (column8_row12373 - 8 * column8_row12565)) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[150] * value;

    // Constraint: ec_op/ec_subset_sum/bit_unpacking/cumulative_bit196.
    tempvar value = (
        column8_row16339 -
        (column8_row16085 - (column8_row16149 + column8_row16149)) * (
            column8_row12565 - (column8_row12629 + column8_row12629)
        )
    ) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[151] * value;

    // Constraint: ec_op/ec_subset_sum/bit_unpacking/zeroes_between_ones196.
    tempvar value = (
        (column8_row16085 - (column8_row16149 + column8_row16149)) * (
            column8_row12629 - 18014398509481984 * column8_row16085
        )
    ) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[152] * value;

    // Constraint: ec_op/ec_subset_sum/booleanity_test.
    tempvar value = (ec_op__ec_subset_sum__bit_0 * (ec_op__ec_subset_sum__bit_0 - 1)) * domain21 /
        domain6;
    tempvar total_sum = total_sum + constraint_coefficients[153] * value;

    // Constraint: ec_op/ec_subset_sum/bit_extraction_end.
    tempvar value = (column8_row21) / domain24;
    tempvar total_sum = total_sum + constraint_coefficients[154] * value;

    // Constraint: ec_op/ec_subset_sum/zeros_tail.
    tempvar value = (column8_row21) / domain21;
    tempvar total_sum = total_sum + constraint_coefficients[155] * value;

    // Constraint: ec_op/ec_subset_sum/add_points/slope.
    tempvar value = (
        ec_op__ec_subset_sum__bit_0 * (column8_row37 - column8_row25) -
        column8_row11 * (column8_row5 - column8_row41)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[156] * value;

    // Constraint: ec_op/ec_subset_sum/add_points/x.
    tempvar value = (
        column8_row11 * column8_row11 -
        ec_op__ec_subset_sum__bit_0 * (column8_row5 + column8_row41 + column8_row69)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[157] * value;

    // Constraint: ec_op/ec_subset_sum/add_points/y.
    tempvar value = (
        ec_op__ec_subset_sum__bit_0 * (column8_row37 + column8_row101) -
        column8_row11 * (column8_row5 - column8_row69)
    ) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[158] * value;

    // Constraint: ec_op/ec_subset_sum/add_points/x_diff_inv.
    tempvar value = (column8_row43 * (column8_row5 - column8_row41) - 1) * domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[159] * value;

    // Constraint: ec_op/ec_subset_sum/copy_point/x.
    tempvar value = (ec_op__ec_subset_sum__bit_neg_0 * (column8_row69 - column8_row5)) * domain21 /
        domain6;
    tempvar total_sum = total_sum + constraint_coefficients[160] * value;

    // Constraint: ec_op/ec_subset_sum/copy_point/y.
    tempvar value = (ec_op__ec_subset_sum__bit_neg_0 * (column8_row101 - column8_row37)) *
        domain21 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[161] * value;

    // Constraint: ec_op/get_m.
    tempvar value = (column8_row21 - column5_row10631) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[162] * value;

    // Constraint: ec_op/get_p_x.
    tempvar value = (column5_row8583 - column8_row5) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[163] * value;

    // Constraint: ec_op/get_p_y.
    tempvar value = (column5_row4487 - column8_row37) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[164] * value;

    // Constraint: ec_op/set_r_x.
    tempvar value = (column5_row6535 - column8_row16325) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[165] * value;

    // Constraint: ec_op/set_r_y.
    tempvar value = (column5_row14727 - column8_row16357) / domain23;
    tempvar total_sum = total_sum + constraint_coefficients[166] * value;

    // Constraint: poseidon/param_0/init_input_output_addr.
    tempvar value = (column5_row38 - global_values.initial_poseidon_addr) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[167] * value;

    // Constraint: poseidon/param_0/addr_input_output_step.
    tempvar value = (column5_row294 - (column5_row38 + 3)) * domain34 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[168] * value;

    // Constraint: poseidon/param_1/init_input_output_addr.
    tempvar value = (column5_row166 - (global_values.initial_poseidon_addr + 1)) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[169] * value;

    // Constraint: poseidon/param_1/addr_input_output_step.
    tempvar value = (column5_row422 - (column5_row166 + 3)) * domain34 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[170] * value;

    // Constraint: poseidon/param_2/init_input_output_addr.
    tempvar value = (column5_row102 - (global_values.initial_poseidon_addr + 2)) / domain29;
    tempvar total_sum = total_sum + constraint_coefficients[171] * value;

    // Constraint: poseidon/param_2/addr_input_output_step.
    tempvar value = (column5_row358 - (column5_row102 + 3)) * domain34 / domain8;
    tempvar total_sum = total_sum + constraint_coefficients[172] * value;

    // Constraint: poseidon/poseidon/full_rounds_state0_squaring.
    tempvar value = (column8_row53 * column8_row53 - column8_row29) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[173] * value;

    // Constraint: poseidon/poseidon/full_rounds_state1_squaring.
    tempvar value = (column8_row13 * column8_row13 - column8_row61) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[174] * value;

    // Constraint: poseidon/poseidon/full_rounds_state2_squaring.
    tempvar value = (column8_row45 * column8_row45 - column8_row3) / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[175] * value;

    // Constraint: poseidon/poseidon/partial_rounds_state0_squaring.
    tempvar value = (column7_row3 * column7_row3 - column7_row7) / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[176] * value;

    // Constraint: poseidon/poseidon/partial_rounds_state1_squaring.
    tempvar value = (column8_row6 * column8_row6 - column8_row14) * domain15 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[177] * value;

    // Constraint: poseidon/poseidon/add_first_round_key0.
    tempvar value = (
        column5_row39 +
        2950795762459345168613727575620414179244544320470208355568817838579231751791 -
        column8_row53
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[178] * value;

    // Constraint: poseidon/poseidon/add_first_round_key1.
    tempvar value = (
        column5_row167 +
        1587446564224215276866294500450702039420286416111469274423465069420553242820 -
        column8_row13
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[179] * value;

    // Constraint: poseidon/poseidon/add_first_round_key2.
    tempvar value = (
        column5_row103 +
        1645965921169490687904413452218868659025437693527479459426157555728339600137 -
        column8_row45
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[180] * value;

    // Constraint: poseidon/poseidon/full_round0.
    tempvar value = (
        column8_row117 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state1_cubed_0 +
            poseidon__poseidon__full_rounds_state2_cubed_0 +
            global_values.poseidon__poseidon__full_round_key0
        )
    ) * domain11 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[181] * value;

    // Constraint: poseidon/poseidon/full_round1.
    tempvar value = (
        column8_row77 +
        poseidon__poseidon__full_rounds_state1_cubed_0 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state2_cubed_0 +
            global_values.poseidon__poseidon__full_round_key1
        )
    ) * domain11 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[182] * value;

    // Constraint: poseidon/poseidon/full_round2.
    tempvar value = (
        column8_row109 +
        poseidon__poseidon__full_rounds_state2_cubed_0 +
        poseidon__poseidon__full_rounds_state2_cubed_0 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_0 +
            poseidon__poseidon__full_rounds_state1_cubed_0 +
            global_values.poseidon__poseidon__full_round_key2
        )
    ) * domain11 / domain6;
    tempvar total_sum = total_sum + constraint_coefficients[183] * value;

    // Constraint: poseidon/poseidon/last_full_round0.
    tempvar value = (
        column5_row295 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state1_cubed_7 +
            poseidon__poseidon__full_rounds_state2_cubed_7
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[184] * value;

    // Constraint: poseidon/poseidon/last_full_round1.
    tempvar value = (
        column5_row423 +
        poseidon__poseidon__full_rounds_state1_cubed_7 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state2_cubed_7
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[185] * value;

    // Constraint: poseidon/poseidon/last_full_round2.
    tempvar value = (
        column5_row359 +
        poseidon__poseidon__full_rounds_state2_cubed_7 +
        poseidon__poseidon__full_rounds_state2_cubed_7 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_7 +
            poseidon__poseidon__full_rounds_state1_cubed_7
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[186] * value;

    // Constraint: poseidon/poseidon/copy_partial_rounds0_i0.
    tempvar value = (column7_row491 - column8_row6) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[187] * value;

    // Constraint: poseidon/poseidon/copy_partial_rounds0_i1.
    tempvar value = (column7_row499 - column8_row22) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[188] * value;

    // Constraint: poseidon/poseidon/copy_partial_rounds0_i2.
    tempvar value = (column7_row507 - column8_row38) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[189] * value;

    // Constraint: poseidon/poseidon/margin_full_to_partial0.
    tempvar value = (
        column7_row3 +
        poseidon__poseidon__full_rounds_state2_cubed_3 +
        poseidon__poseidon__full_rounds_state2_cubed_3 -
        (
            poseidon__poseidon__full_rounds_state0_cubed_3 +
            poseidon__poseidon__full_rounds_state1_cubed_3 +
            2121140748740143694053732746913428481442990369183417228688865837805149503386
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[190] * value;

    // Constraint: poseidon/poseidon/margin_full_to_partial1.
    tempvar value = (
        column7_row11 -
        (
            3618502788666131213697322783095070105623107215331596699973092056135872020477 *
            poseidon__poseidon__full_rounds_state1_cubed_3 +
            10 * poseidon__poseidon__full_rounds_state2_cubed_3 +
            4 * column7_row3 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state0_cubed_0 +
            2006642341318481906727563724340978325665491359415674592697055778067937914672
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[191] * value;

    // Constraint: poseidon/poseidon/margin_full_to_partial2.
    tempvar value = (
        column7_row19 -
        (
            8 * poseidon__poseidon__full_rounds_state2_cubed_3 +
            4 * column7_row3 +
            6 * poseidon__poseidon__partial_rounds_state0_cubed_0 +
            column7_row11 +
            column7_row11 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state0_cubed_1 +
            427751140904099001132521606468025610873158555767197326325930641757709538586
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[192] * value;

    // Constraint: poseidon/poseidon/partial_round0.
    tempvar value = (
        column7_row27 -
        (
            8 * poseidon__poseidon__partial_rounds_state0_cubed_0 +
            4 * column7_row11 +
            6 * poseidon__poseidon__partial_rounds_state0_cubed_1 +
            column7_row19 +
            column7_row19 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state0_cubed_2 +
            global_values.poseidon__poseidon__partial_round_key0
        )
    ) * domain16 / domain3;
    tempvar total_sum = total_sum + constraint_coefficients[193] * value;

    // Constraint: poseidon/poseidon/partial_round1.
    tempvar value = (
        column8_row54 -
        (
            8 * poseidon__poseidon__partial_rounds_state1_cubed_0 +
            4 * column8_row22 +
            6 * poseidon__poseidon__partial_rounds_state1_cubed_1 +
            column8_row38 +
            column8_row38 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state1_cubed_2 +
            global_values.poseidon__poseidon__partial_round_key1
        )
    ) * domain17 / domain5;
    tempvar total_sum = total_sum + constraint_coefficients[194] * value;

    // Constraint: poseidon/poseidon/margin_partial_to_full0.
    tempvar value = (
        column8_row309 -
        (
            16 * poseidon__poseidon__partial_rounds_state1_cubed_19 +
            8 * column8_row326 +
            16 * poseidon__poseidon__partial_rounds_state1_cubed_20 +
            6 * column8_row342 +
            poseidon__poseidon__partial_rounds_state1_cubed_21 +
            560279373700919169769089400651532183647886248799764942664266404650165812023
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[195] * value;

    // Constraint: poseidon/poseidon/margin_partial_to_full1.
    tempvar value = (
        column8_row269 -
        (
            4 * poseidon__poseidon__partial_rounds_state1_cubed_20 +
            column8_row342 +
            column8_row342 +
            poseidon__poseidon__partial_rounds_state1_cubed_21 +
            1401754474293352309994371631695783042590401941592571735921592823982231996415
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[196] * value;

    // Constraint: poseidon/poseidon/margin_partial_to_full2.
    tempvar value = (
        column8_row301 -
        (
            8 * poseidon__poseidon__partial_rounds_state1_cubed_19 +
            4 * column8_row326 +
            6 * poseidon__poseidon__partial_rounds_state1_cubed_20 +
            column8_row342 +
            column8_row342 +
            3618502788666131213697322783095070105623107215331596699973092056135872020479 *
            poseidon__poseidon__partial_rounds_state1_cubed_21 +
            1246177936547655338400308396717835700699368047388302793172818304164989556526
        )
    ) / domain13;
    tempvar total_sum = total_sum + constraint_coefficients[197] * value;

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
    let (local pow1) = pow(trace_generator, 32715);
    let (local pow2) = pow(trace_generator, 32667);
    let (local pow3) = pow(trace_generator, 32647);
    let (local pow4) = pow(trace_generator, 16325);
    let (local pow5) = pow(trace_generator, 16149);
    let (local pow6) = pow(trace_generator, 16085);
    let (local pow7) = pow(trace_generator, 12373);
    let (local pow8) = pow(trace_generator, 12309);
    let (local pow9) = pow(trace_generator, 24966);
    let (local pow10) = pow(trace_generator, 16774);
    let (local pow11) = pow(trace_generator, 14726);
    let (local pow12) = pow(trace_generator, 10630);
    let (local pow13) = pow(trace_generator, 8582);
    let (local pow14) = pow(trace_generator, 6534);
    let (local pow15) = pow(trace_generator, 4486);
    let (local pow16) = pow(trace_generator, 2438);
    let (local pow17) = pow(trace_generator, 1);
    local pow18 = pow11 * pow17;  // pow(trace_generator, 14727).
    local pow19 = pow12 * pow17;  // pow(trace_generator, 10631).
    local pow20 = pow13 * pow17;  // pow(trace_generator, 8583).
    local pow21 = pow14 * pow17;  // pow(trace_generator, 6535).
    local pow22 = pow15 * pow17;  // pow(trace_generator, 4487).
    local pow23 = pow16 * pow17;  // pow(trace_generator, 2439).
    local pow24 = pow17 * pow17;  // pow(trace_generator, 2).
    local pow25 = pow17 * pow24;  // pow(trace_generator, 3).
    local pow26 = pow17 * pow25;  // pow(trace_generator, 4).
    local pow27 = pow17 * pow26;  // pow(trace_generator, 5).
    local pow28 = pow17 * pow27;  // pow(trace_generator, 6).
    local pow29 = pow4 * pow28;  // pow(trace_generator, 16331).
    local pow30 = pow17 * pow28;  // pow(trace_generator, 7).
    local pow31 = pow17 * pow30;  // pow(trace_generator, 8).
    local pow32 = pow17 * pow31;  // pow(trace_generator, 9).
    local pow33 = pow17 * pow32;  // pow(trace_generator, 10).
    local pow34 = pow17 * pow33;  // pow(trace_generator, 11).
    local pow35 = pow17 * pow34;  // pow(trace_generator, 12).
    local pow36 = pow17 * pow35;  // pow(trace_generator, 13).
    local pow37 = pow17 * pow36;  // pow(trace_generator, 14).
    local pow38 = pow17 * pow37;  // pow(trace_generator, 15).
    local pow39 = pow17 * pow38;  // pow(trace_generator, 16).
    local pow40 = pow17 * pow39;  // pow(trace_generator, 17).
    local pow41 = pow24 * pow40;  // pow(trace_generator, 19).
    local pow42 = pow24 * pow41;  // pow(trace_generator, 21).
    local pow43 = pow17 * pow42;  // pow(trace_generator, 22).
    local pow44 = pow17 * pow43;  // pow(trace_generator, 23).
    local pow45 = pow17 * pow44;  // pow(trace_generator, 24).
    local pow46 = pow17 * pow45;  // pow(trace_generator, 25).
    local pow47 = pow24 * pow46;  // pow(trace_generator, 27).
    local pow48 = pow24 * pow47;  // pow(trace_generator, 29).
    local pow49 = pow17 * pow48;  // pow(trace_generator, 30).
    local pow50 = pow25 * pow49;  // pow(trace_generator, 33).
    local pow51 = pow24 * pow50;  // pow(trace_generator, 35).
    local pow52 = pow24 * pow51;  // pow(trace_generator, 37).
    local pow53 = pow17 * pow52;  // pow(trace_generator, 38).
    local pow54 = pow17 * pow53;  // pow(trace_generator, 39).
    local pow55 = pow24 * pow54;  // pow(trace_generator, 41).
    local pow56 = pow24 * pow55;  // pow(trace_generator, 43).
    local pow57 = pow17 * pow56;  // pow(trace_generator, 44).
    local pow58 = pow17 * pow57;  // pow(trace_generator, 45).
    local pow59 = pow17 * pow58;  // pow(trace_generator, 46).
    local pow60 = pow25 * pow59;  // pow(trace_generator, 49).
    local pow61 = pow24 * pow60;  // pow(trace_generator, 51).
    local pow62 = pow24 * pow61;  // pow(trace_generator, 53).
    local pow63 = pow17 * pow62;  // pow(trace_generator, 54).
    local pow64 = pow1 * pow28;  // pow(trace_generator, 32721).
    local pow65 = pow1 * pow39;  // pow(trace_generator, 32731).
    local pow66 = pow39 * pow65;  // pow(trace_generator, 32747).
    local pow67 = pow1 * pow53;  // pow(trace_generator, 32753).
    local pow68 = pow33 * pow67;  // pow(trace_generator, 32763).
    local pow69 = pow25 * pow63;  // pow(trace_generator, 57).
    local pow70 = pow24 * pow69;  // pow(trace_generator, 59).
    local pow71 = pow24 * pow70;  // pow(trace_generator, 61).
    local pow72 = pow26 * pow71;  // pow(trace_generator, 65).
    local pow73 = pow26 * pow72;  // pow(trace_generator, 69).
    local pow74 = pow17 * pow73;  // pow(trace_generator, 70).
    local pow75 = pow17 * pow74;  // pow(trace_generator, 71).
    local pow76 = pow24 * pow75;  // pow(trace_generator, 73).
    local pow77 = pow25 * pow76;  // pow(trace_generator, 76).
    local pow78 = pow17 * pow77;  // pow(trace_generator, 77).
    local pow79 = pow26 * pow78;  // pow(trace_generator, 81).
    local pow80 = pow26 * pow79;  // pow(trace_generator, 85).
    local pow81 = pow26 * pow80;  // pow(trace_generator, 89).
    local pow82 = pow24 * pow81;  // pow(trace_generator, 91).
    local pow83 = pow28 * pow82;  // pow(trace_generator, 97).
    local pow84 = pow26 * pow83;  // pow(trace_generator, 101).
    local pow85 = pow17 * pow84;  // pow(trace_generator, 102).
    local pow86 = pow17 * pow85;  // pow(trace_generator, 103).
    local pow87 = pow24 * pow86;  // pow(trace_generator, 105).
    local pow88 = pow25 * pow87;  // pow(trace_generator, 108).
    local pow89 = pow17 * pow88;  // pow(trace_generator, 109).
    local pow90 = pow26 * pow89;  // pow(trace_generator, 113).
    local pow91 = pow26 * pow90;  // pow(trace_generator, 117).
    local pow92 = pow28 * pow91;  // pow(trace_generator, 123).
    local pow93 = pow28 * pow92;  // pow(trace_generator, 129).
    local pow94 = pow27 * pow93;  // pow(trace_generator, 134).
    local pow95 = pow17 * pow94;  // pow(trace_generator, 135).
    local pow96 = pow27 * pow95;  // pow(trace_generator, 140).
    local pow97 = pow27 * pow96;  // pow(trace_generator, 145).
    local pow98 = pow33 * pow97;  // pow(trace_generator, 155).
    local pow99 = pow28 * pow98;  // pow(trace_generator, 161).
    local pow100 = pow27 * pow99;  // pow(trace_generator, 166).
    local pow101 = pow17 * pow100;  // pow(trace_generator, 167).
    local pow102 = pow27 * pow101;  // pow(trace_generator, 172).
    local pow103 = pow27 * pow102;  // pow(trace_generator, 177).
    local pow104 = pow33 * pow103;  // pow(trace_generator, 187).
    local pow105 = pow27 * pow104;  // pow(trace_generator, 192).
    local pow106 = pow17 * pow105;  // pow(trace_generator, 193).
    local pow107 = pow24 * pow106;  // pow(trace_generator, 195).
    local pow108 = pow17 * pow107;  // pow(trace_generator, 196).
    local pow109 = pow17 * pow108;  // pow(trace_generator, 197).
    local pow110 = pow17 * pow109;  // pow(trace_generator, 198).
    local pow111 = pow17 * pow110;  // pow(trace_generator, 199).
    local pow112 = pow27 * pow111;  // pow(trace_generator, 204).
    local pow113 = pow17 * pow112;  // pow(trace_generator, 205).
    local pow114 = pow26 * pow113;  // pow(trace_generator, 209).
    local pow115 = pow33 * pow114;  // pow(trace_generator, 219).
    local pow116 = pow24 * pow115;  // pow(trace_generator, 221).
    local pow117 = pow26 * pow116;  // pow(trace_generator, 225).
    local pow118 = pow34 * pow117;  // pow(trace_generator, 236).
    local pow119 = pow17 * pow118;  // pow(trace_generator, 237).
    local pow120 = pow26 * pow119;  // pow(trace_generator, 241).
    local pow121 = pow26 * pow120;  // pow(trace_generator, 245).
    local pow122 = pow28 * pow121;  // pow(trace_generator, 251).
    local pow123 = pow17 * pow122;  // pow(trace_generator, 252).
    local pow124 = pow4 * pow35;  // pow(trace_generator, 16337).
    local pow125 = pow4 * pow37;  // pow(trace_generator, 16339).
    local pow126 = pow4 * pow49;  // pow(trace_generator, 16355).
    local pow127 = pow24 * pow126;  // pow(trace_generator, 16357).
    local pow128 = pow4 * pow53;  // pow(trace_generator, 16363).
    local pow129 = pow4 * pow57;  // pow(trace_generator, 16369).
    local pow130 = pow4 * pow59;  // pow(trace_generator, 16371).
    local pow131 = pow5 * pow118;  // pow(trace_generator, 16385).
    local pow132 = pow59 * pow130;  // pow(trace_generator, 16417).
    local pow133 = pow17 * pow123;  // pow(trace_generator, 253).
    local pow134 = pow24 * pow133;  // pow(trace_generator, 255).
    local pow135 = pow17 * pow134;  // pow(trace_generator, 256).
    local pow136 = pow17 * pow135;  // pow(trace_generator, 257).
    local pow137 = pow7 * pow135;  // pow(trace_generator, 12629).
    local pow138 = pow7 * pow105;  // pow(trace_generator, 12565).
    local pow139 = pow60 * pow137;  // pow(trace_generator, 12678).
    local pow140 = pow17 * pow139;  // pow(trace_generator, 12679).
    local pow141 = pow27 * pow136;  // pow(trace_generator, 262).
    local pow142 = pow17 * pow141;  // pow(trace_generator, 263).
    local pow143 = pow24 * pow142;  // pow(trace_generator, 265).
    local pow144 = pow26 * pow143;  // pow(trace_generator, 269).
    local pow145 = pow46 * pow144;  // pow(trace_generator, 294).
    local pow146 = pow17 * pow145;  // pow(trace_generator, 295).
    local pow147 = pow28 * pow146;  // pow(trace_generator, 301).
    local pow148 = pow31 * pow147;  // pow(trace_generator, 309).
    local pow149 = pow17 * pow148;  // pow(trace_generator, 310).
    local pow150 = pow31 * pow149;  // pow(trace_generator, 318).
    local pow151 = pow90 * pow148;  // pow(trace_generator, 422).
    local pow152 = pow79 * pow148;  // pow(trace_generator, 390).
    local pow153 = pow31 * pow150;  // pow(trace_generator, 326).
    local pow154 = pow31 * pow153;  // pow(trace_generator, 334).
    local pow155 = pow31 * pow154;  // pow(trace_generator, 342).
    local pow156 = pow31 * pow155;  // pow(trace_generator, 350).
    local pow157 = pow31 * pow156;  // pow(trace_generator, 358).
    local pow158 = pow17 * pow151;  // pow(trace_generator, 423).
    local pow159 = pow17 * pow152;  // pow(trace_generator, 391).
    local pow160 = pow17 * pow157;  // pow(trace_generator, 359).
    local pow161 = pow10 * pow17;  // pow(trace_generator, 16775).
    local pow162 = pow48 * pow151;  // pow(trace_generator, 451).
    local pow163 = pow25 * pow162;  // pow(trace_generator, 454).
    local pow164 = pow30 * pow163;  // pow(trace_generator, 461).
    local pow165 = pow39 * pow164;  // pow(trace_generator, 477).
    local pow166 = pow37 * pow165;  // pow(trace_generator, 491).
    local pow167 = pow24 * pow166;  // pow(trace_generator, 493).
    local pow168 = pow28 * pow167;  // pow(trace_generator, 499).
    local pow169 = pow24 * pow168;  // pow(trace_generator, 501).
    local pow170 = pow28 * pow169;  // pow(trace_generator, 507).
    local pow171 = pow24 * pow170;  // pow(trace_generator, 509).
    local pow172 = pow24 * pow171;  // pow(trace_generator, 511).
    local pow173 = pow2 * pow166;  // pow(trace_generator, 33158).
    local pow174 = pow24 * pow172;  // pow(trace_generator, 513).
    local pow175 = pow27 * pow174;  // pow(trace_generator, 518).
    local pow176 = pow104 * pow175;  // pow(trace_generator, 705).
    local pow177 = pow109 * pow176;  // pow(trace_generator, 902).
    local pow178 = pow28 * pow176;  // pow(trace_generator, 711).
    local pow179 = pow33 * pow178;  // pow(trace_generator, 721).
    local pow180 = pow39 * pow179;  // pow(trace_generator, 737).
    local pow181 = pow39 * pow180;  // pow(trace_generator, 753).
    local pow182 = pow39 * pow181;  // pow(trace_generator, 769).
    local pow183 = pow70 * pow177;  // pow(trace_generator, 961).
    local pow184 = pow27 * pow183;  // pow(trace_generator, 966).
    local pow185 = pow17 * pow184;  // pow(trace_generator, 967).
    local pow186 = pow33 * pow185;  // pow(trace_generator, 977).
    local pow187 = pow121 * pow186;  // pow(trace_generator, 1222).
    local pow188 = pow17 * pow177;  // pow(trace_generator, 903).
    local pow189 = pow39 * pow186;  // pow(trace_generator, 993).
    local pow190 = pow39 * pow189;  // pow(trace_generator, 1009).
    local pow191 = pow25 * pow175;  // pow(trace_generator, 521).
    local pow192 = pow31 * pow182;  // pow(trace_generator, 777).

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

    tempvar value = (column0 - oods_values[1]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[1] * value;

    tempvar value = (column0 - oods_values[2]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[2] * value;

    tempvar value = (column0 - oods_values[3]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[3] * value;

    tempvar value = (column0 - oods_values[4]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[4] * value;

    tempvar value = (column0 - oods_values[5]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[5] * value;

    tempvar value = (column0 - oods_values[6]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[6] * value;

    tempvar value = (column0 - oods_values[7]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[7] * value;

    tempvar value = (column0 - oods_values[8]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[8] * value;

    tempvar value = (column0 - oods_values[9]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[9] * value;

    tempvar value = (column0 - oods_values[10]) / (point - pow33 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[10] * value;

    tempvar value = (column0 - oods_values[11]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[11] * value;

    tempvar value = (column0 - oods_values[12]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[12] * value;

    tempvar value = (column0 - oods_values[13]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[13] * value;

    tempvar value = (column0 - oods_values[14]) / (point - pow37 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[14] * value;

    tempvar value = (column0 - oods_values[15]) / (point - pow38 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[15] * value;

    tempvar value = (column1 - oods_values[16]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[16] * value;

    tempvar value = (column1 - oods_values[17]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[17] * value;

    tempvar value = (column1 - oods_values[18]) / (point - pow134 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[18] * value;

    tempvar value = (column1 - oods_values[19]) / (point - pow135 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[19] * value;

    tempvar value = (column1 - oods_values[20]) / (point - pow172 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[20] * value;

    tempvar value = (column2 - oods_values[21]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[21] * value;

    tempvar value = (column2 - oods_values[22]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[22] * value;

    tempvar value = (column2 - oods_values[23]) / (point - pow134 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[23] * value;

    tempvar value = (column2 - oods_values[24]) / (point - pow135 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[24] * value;

    tempvar value = (column3 - oods_values[25]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[25] * value;

    tempvar value = (column3 - oods_values[26]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[26] * value;

    tempvar value = (column3 - oods_values[27]) / (point - pow105 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[27] * value;

    tempvar value = (column3 - oods_values[28]) / (point - pow106 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[28] * value;

    tempvar value = (column3 - oods_values[29]) / (point - pow108 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[29] * value;

    tempvar value = (column3 - oods_values[30]) / (point - pow109 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[30] * value;

    tempvar value = (column3 - oods_values[31]) / (point - pow122 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[31] * value;

    tempvar value = (column3 - oods_values[32]) / (point - pow123 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[32] * value;

    tempvar value = (column3 - oods_values[33]) / (point - pow135 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[33] * value;

    tempvar value = (column4 - oods_values[34]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[34] * value;

    tempvar value = (column4 - oods_values[35]) / (point - pow134 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[35] * value;

    tempvar value = (column5 - oods_values[36]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[36] * value;

    tempvar value = (column5 - oods_values[37]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[37] * value;

    tempvar value = (column5 - oods_values[38]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[38] * value;

    tempvar value = (column5 - oods_values[39]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[39] * value;

    tempvar value = (column5 - oods_values[40]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[40] * value;

    tempvar value = (column5 - oods_values[41]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[41] * value;

    tempvar value = (column5 - oods_values[42]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[42] * value;

    tempvar value = (column5 - oods_values[43]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[43] * value;

    tempvar value = (column5 - oods_values[44]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[44] * value;

    tempvar value = (column5 - oods_values[45]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[45] * value;

    tempvar value = (column5 - oods_values[46]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[46] * value;

    tempvar value = (column5 - oods_values[47]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[47] * value;

    tempvar value = (column5 - oods_values[48]) / (point - pow39 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[48] * value;

    tempvar value = (column5 - oods_values[49]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[49] * value;

    tempvar value = (column5 - oods_values[50]) / (point - pow54 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[50] * value;

    tempvar value = (column5 - oods_values[51]) / (point - pow74 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[51] * value;

    tempvar value = (column5 - oods_values[52]) / (point - pow75 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[52] * value;

    tempvar value = (column5 - oods_values[53]) / (point - pow85 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[53] * value;

    tempvar value = (column5 - oods_values[54]) / (point - pow86 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[54] * value;

    tempvar value = (column5 - oods_values[55]) / (point - pow94 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[55] * value;

    tempvar value = (column5 - oods_values[56]) / (point - pow95 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[56] * value;

    tempvar value = (column5 - oods_values[57]) / (point - pow100 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[57] * value;

    tempvar value = (column5 - oods_values[58]) / (point - pow101 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[58] * value;

    tempvar value = (column5 - oods_values[59]) / (point - pow110 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[59] * value;

    tempvar value = (column5 - oods_values[60]) / (point - pow111 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[60] * value;

    tempvar value = (column5 - oods_values[61]) / (point - pow141 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[61] * value;

    tempvar value = (column5 - oods_values[62]) / (point - pow142 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[62] * value;

    tempvar value = (column5 - oods_values[63]) / (point - pow145 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[63] * value;

    tempvar value = (column5 - oods_values[64]) / (point - pow146 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[64] * value;

    tempvar value = (column5 - oods_values[65]) / (point - pow153 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[65] * value;

    tempvar value = (column5 - oods_values[66]) / (point - pow157 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[66] * value;

    tempvar value = (column5 - oods_values[67]) / (point - pow160 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[67] * value;

    tempvar value = (column5 - oods_values[68]) / (point - pow152 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[68] * value;

    tempvar value = (column5 - oods_values[69]) / (point - pow159 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[69] * value;

    tempvar value = (column5 - oods_values[70]) / (point - pow151 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[70] * value;

    tempvar value = (column5 - oods_values[71]) / (point - pow158 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[71] * value;

    tempvar value = (column5 - oods_values[72]) / (point - pow163 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[72] * value;

    tempvar value = (column5 - oods_values[73]) / (point - pow175 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[73] * value;

    tempvar value = (column5 - oods_values[74]) / (point - pow178 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[74] * value;

    tempvar value = (column5 - oods_values[75]) / (point - pow177 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[75] * value;

    tempvar value = (column5 - oods_values[76]) / (point - pow188 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[76] * value;

    tempvar value = (column5 - oods_values[77]) / (point - pow184 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[77] * value;

    tempvar value = (column5 - oods_values[78]) / (point - pow185 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[78] * value;

    tempvar value = (column5 - oods_values[79]) / (point - pow187 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[79] * value;

    tempvar value = (column5 - oods_values[80]) / (point - pow16 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[80] * value;

    tempvar value = (column5 - oods_values[81]) / (point - pow23 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[81] * value;

    tempvar value = (column5 - oods_values[82]) / (point - pow15 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[82] * value;

    tempvar value = (column5 - oods_values[83]) / (point - pow22 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[83] * value;

    tempvar value = (column5 - oods_values[84]) / (point - pow14 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[84] * value;

    tempvar value = (column5 - oods_values[85]) / (point - pow21 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[85] * value;

    tempvar value = (column5 - oods_values[86]) / (point - pow13 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[86] * value;

    tempvar value = (column5 - oods_values[87]) / (point - pow20 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[87] * value;

    tempvar value = (column5 - oods_values[88]) / (point - pow12 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[88] * value;

    tempvar value = (column5 - oods_values[89]) / (point - pow19 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[89] * value;

    tempvar value = (column5 - oods_values[90]) / (point - pow139 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[90] * value;

    tempvar value = (column5 - oods_values[91]) / (point - pow140 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[91] * value;

    tempvar value = (column5 - oods_values[92]) / (point - pow11 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[92] * value;

    tempvar value = (column5 - oods_values[93]) / (point - pow18 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[93] * value;

    tempvar value = (column5 - oods_values[94]) / (point - pow10 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[94] * value;

    tempvar value = (column5 - oods_values[95]) / (point - pow161 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[95] * value;

    tempvar value = (column5 - oods_values[96]) / (point - pow9 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[96] * value;

    tempvar value = (column5 - oods_values[97]) / (point - pow173 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[97] * value;

    tempvar value = (column6 - oods_values[98]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[98] * value;

    tempvar value = (column6 - oods_values[99]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[99] * value;

    tempvar value = (column6 - oods_values[100]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[100] * value;

    tempvar value = (column6 - oods_values[101]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[101] * value;

    tempvar value = (column7 - oods_values[102]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[102] * value;

    tempvar value = (column7 - oods_values[103]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[103] * value;

    tempvar value = (column7 - oods_values[104]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[104] * value;

    tempvar value = (column7 - oods_values[105]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[105] * value;

    tempvar value = (column7 - oods_values[106]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[106] * value;

    tempvar value = (column7 - oods_values[107]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[107] * value;

    tempvar value = (column7 - oods_values[108]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[108] * value;

    tempvar value = (column7 - oods_values[109]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[109] * value;

    tempvar value = (column7 - oods_values[110]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[110] * value;

    tempvar value = (column7 - oods_values[111]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[111] * value;

    tempvar value = (column7 - oods_values[112]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[112] * value;

    tempvar value = (column7 - oods_values[113]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[113] * value;

    tempvar value = (column7 - oods_values[114]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[114] * value;

    tempvar value = (column7 - oods_values[115]) / (point - pow38 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[115] * value;

    tempvar value = (column7 - oods_values[116]) / (point - pow40 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[116] * value;

    tempvar value = (column7 - oods_values[117]) / (point - pow41 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[117] * value;

    tempvar value = (column7 - oods_values[118]) / (point - pow44 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[118] * value;

    tempvar value = (column7 - oods_values[119]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[119] * value;

    tempvar value = (column7 - oods_values[120]) / (point - pow50 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[120] * value;

    tempvar value = (column7 - oods_values[121]) / (point - pow57 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[121] * value;

    tempvar value = (column7 - oods_values[122]) / (point - pow60 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[122] * value;

    tempvar value = (column7 - oods_values[123]) / (point - pow72 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[123] * value;

    tempvar value = (column7 - oods_values[124]) / (point - pow77 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[124] * value;

    tempvar value = (column7 - oods_values[125]) / (point - pow79 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[125] * value;

    tempvar value = (column7 - oods_values[126]) / (point - pow83 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[126] * value;

    tempvar value = (column7 - oods_values[127]) / (point - pow88 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[127] * value;

    tempvar value = (column7 - oods_values[128]) / (point - pow90 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[128] * value;

    tempvar value = (column7 - oods_values[129]) / (point - pow93 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[129] * value;

    tempvar value = (column7 - oods_values[130]) / (point - pow96 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[130] * value;

    tempvar value = (column7 - oods_values[131]) / (point - pow97 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[131] * value;

    tempvar value = (column7 - oods_values[132]) / (point - pow99 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[132] * value;

    tempvar value = (column7 - oods_values[133]) / (point - pow102 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[133] * value;

    tempvar value = (column7 - oods_values[134]) / (point - pow103 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[134] * value;

    tempvar value = (column7 - oods_values[135]) / (point - pow106 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[135] * value;

    tempvar value = (column7 - oods_values[136]) / (point - pow112 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[136] * value;

    tempvar value = (column7 - oods_values[137]) / (point - pow114 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[137] * value;

    tempvar value = (column7 - oods_values[138]) / (point - pow117 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[138] * value;

    tempvar value = (column7 - oods_values[139]) / (point - pow118 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[139] * value;

    tempvar value = (column7 - oods_values[140]) / (point - pow120 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[140] * value;

    tempvar value = (column7 - oods_values[141]) / (point - pow136 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[141] * value;

    tempvar value = (column7 - oods_values[142]) / (point - pow143 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[142] * value;

    tempvar value = (column7 - oods_values[143]) / (point - pow166 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[143] * value;

    tempvar value = (column7 - oods_values[144]) / (point - pow168 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[144] * value;

    tempvar value = (column7 - oods_values[145]) / (point - pow170 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[145] * value;

    tempvar value = (column7 - oods_values[146]) / (point - pow174 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[146] * value;

    tempvar value = (column7 - oods_values[147]) / (point - pow191 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[147] * value;

    tempvar value = (column7 - oods_values[148]) / (point - pow176 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[148] * value;

    tempvar value = (column7 - oods_values[149]) / (point - pow179 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[149] * value;

    tempvar value = (column7 - oods_values[150]) / (point - pow180 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[150] * value;

    tempvar value = (column7 - oods_values[151]) / (point - pow181 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[151] * value;

    tempvar value = (column7 - oods_values[152]) / (point - pow182 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[152] * value;

    tempvar value = (column7 - oods_values[153]) / (point - pow192 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[153] * value;

    tempvar value = (column7 - oods_values[154]) / (point - pow183 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[154] * value;

    tempvar value = (column7 - oods_values[155]) / (point - pow186 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[155] * value;

    tempvar value = (column7 - oods_values[156]) / (point - pow189 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[156] * value;

    tempvar value = (column7 - oods_values[157]) / (point - pow190 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[157] * value;

    tempvar value = (column8 - oods_values[158]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[158] * value;

    tempvar value = (column8 - oods_values[159]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[159] * value;

    tempvar value = (column8 - oods_values[160]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[160] * value;

    tempvar value = (column8 - oods_values[161]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[161] * value;

    tempvar value = (column8 - oods_values[162]) / (point - pow26 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[162] * value;

    tempvar value = (column8 - oods_values[163]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[163] * value;

    tempvar value = (column8 - oods_values[164]) / (point - pow28 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[164] * value;

    tempvar value = (column8 - oods_values[165]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[165] * value;

    tempvar value = (column8 - oods_values[166]) / (point - pow31 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[166] * value;

    tempvar value = (column8 - oods_values[167]) / (point - pow32 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[167] * value;

    tempvar value = (column8 - oods_values[168]) / (point - pow33 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[168] * value;

    tempvar value = (column8 - oods_values[169]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[169] * value;

    tempvar value = (column8 - oods_values[170]) / (point - pow35 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[170] * value;

    tempvar value = (column8 - oods_values[171]) / (point - pow36 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[171] * value;

    tempvar value = (column8 - oods_values[172]) / (point - pow37 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[172] * value;

    tempvar value = (column8 - oods_values[173]) / (point - pow39 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[173] * value;

    tempvar value = (column8 - oods_values[174]) / (point - pow40 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[174] * value;

    tempvar value = (column8 - oods_values[175]) / (point - pow41 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[175] * value;

    tempvar value = (column8 - oods_values[176]) / (point - pow42 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[176] * value;

    tempvar value = (column8 - oods_values[177]) / (point - pow43 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[177] * value;

    tempvar value = (column8 - oods_values[178]) / (point - pow45 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[178] * value;

    tempvar value = (column8 - oods_values[179]) / (point - pow46 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[179] * value;

    tempvar value = (column8 - oods_values[180]) / (point - pow47 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[180] * value;

    tempvar value = (column8 - oods_values[181]) / (point - pow48 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[181] * value;

    tempvar value = (column8 - oods_values[182]) / (point - pow49 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[182] * value;

    tempvar value = (column8 - oods_values[183]) / (point - pow50 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[183] * value;

    tempvar value = (column8 - oods_values[184]) / (point - pow51 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[184] * value;

    tempvar value = (column8 - oods_values[185]) / (point - pow52 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[185] * value;

    tempvar value = (column8 - oods_values[186]) / (point - pow53 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[186] * value;

    tempvar value = (column8 - oods_values[187]) / (point - pow55 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[187] * value;

    tempvar value = (column8 - oods_values[188]) / (point - pow56 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[188] * value;

    tempvar value = (column8 - oods_values[189]) / (point - pow58 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[189] * value;

    tempvar value = (column8 - oods_values[190]) / (point - pow59 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[190] * value;

    tempvar value = (column8 - oods_values[191]) / (point - pow60 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[191] * value;

    tempvar value = (column8 - oods_values[192]) / (point - pow61 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[192] * value;

    tempvar value = (column8 - oods_values[193]) / (point - pow62 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[193] * value;

    tempvar value = (column8 - oods_values[194]) / (point - pow63 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[194] * value;

    tempvar value = (column8 - oods_values[195]) / (point - pow69 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[195] * value;

    tempvar value = (column8 - oods_values[196]) / (point - pow70 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[196] * value;

    tempvar value = (column8 - oods_values[197]) / (point - pow71 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[197] * value;

    tempvar value = (column8 - oods_values[198]) / (point - pow72 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[198] * value;

    tempvar value = (column8 - oods_values[199]) / (point - pow73 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[199] * value;

    tempvar value = (column8 - oods_values[200]) / (point - pow75 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[200] * value;

    tempvar value = (column8 - oods_values[201]) / (point - pow76 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[201] * value;

    tempvar value = (column8 - oods_values[202]) / (point - pow78 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[202] * value;

    tempvar value = (column8 - oods_values[203]) / (point - pow79 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[203] * value;

    tempvar value = (column8 - oods_values[204]) / (point - pow80 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[204] * value;

    tempvar value = (column8 - oods_values[205]) / (point - pow81 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[205] * value;

    tempvar value = (column8 - oods_values[206]) / (point - pow82 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[206] * value;

    tempvar value = (column8 - oods_values[207]) / (point - pow83 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[207] * value;

    tempvar value = (column8 - oods_values[208]) / (point - pow84 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[208] * value;

    tempvar value = (column8 - oods_values[209]) / (point - pow87 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[209] * value;

    tempvar value = (column8 - oods_values[210]) / (point - pow89 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[210] * value;

    tempvar value = (column8 - oods_values[211]) / (point - pow90 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[211] * value;

    tempvar value = (column8 - oods_values[212]) / (point - pow91 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[212] * value;

    tempvar value = (column8 - oods_values[213]) / (point - pow92 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[213] * value;

    tempvar value = (column8 - oods_values[214]) / (point - pow98 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[214] * value;

    tempvar value = (column8 - oods_values[215]) / (point - pow104 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[215] * value;

    tempvar value = (column8 - oods_values[216]) / (point - pow107 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[216] * value;

    tempvar value = (column8 - oods_values[217]) / (point - pow113 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[217] * value;

    tempvar value = (column8 - oods_values[218]) / (point - pow115 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[218] * value;

    tempvar value = (column8 - oods_values[219]) / (point - pow116 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[219] * value;

    tempvar value = (column8 - oods_values[220]) / (point - pow119 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[220] * value;

    tempvar value = (column8 - oods_values[221]) / (point - pow121 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[221] * value;

    tempvar value = (column8 - oods_values[222]) / (point - pow133 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[222] * value;

    tempvar value = (column8 - oods_values[223]) / (point - pow144 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[223] * value;

    tempvar value = (column8 - oods_values[224]) / (point - pow147 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[224] * value;

    tempvar value = (column8 - oods_values[225]) / (point - pow148 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[225] * value;

    tempvar value = (column8 - oods_values[226]) / (point - pow149 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[226] * value;

    tempvar value = (column8 - oods_values[227]) / (point - pow150 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[227] * value;

    tempvar value = (column8 - oods_values[228]) / (point - pow153 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[228] * value;

    tempvar value = (column8 - oods_values[229]) / (point - pow154 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[229] * value;

    tempvar value = (column8 - oods_values[230]) / (point - pow155 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[230] * value;

    tempvar value = (column8 - oods_values[231]) / (point - pow156 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[231] * value;

    tempvar value = (column8 - oods_values[232]) / (point - pow162 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[232] * value;

    tempvar value = (column8 - oods_values[233]) / (point - pow164 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[233] * value;

    tempvar value = (column8 - oods_values[234]) / (point - pow165 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[234] * value;

    tempvar value = (column8 - oods_values[235]) / (point - pow167 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[235] * value;

    tempvar value = (column8 - oods_values[236]) / (point - pow169 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[236] * value;

    tempvar value = (column8 - oods_values[237]) / (point - pow171 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[237] * value;

    tempvar value = (column8 - oods_values[238]) / (point - pow8 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[238] * value;

    tempvar value = (column8 - oods_values[239]) / (point - pow7 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[239] * value;

    tempvar value = (column8 - oods_values[240]) / (point - pow138 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[240] * value;

    tempvar value = (column8 - oods_values[241]) / (point - pow137 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[241] * value;

    tempvar value = (column8 - oods_values[242]) / (point - pow6 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[242] * value;

    tempvar value = (column8 - oods_values[243]) / (point - pow5 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[243] * value;

    tempvar value = (column8 - oods_values[244]) / (point - pow4 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[244] * value;

    tempvar value = (column8 - oods_values[245]) / (point - pow29 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[245] * value;

    tempvar value = (column8 - oods_values[246]) / (point - pow124 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[246] * value;

    tempvar value = (column8 - oods_values[247]) / (point - pow125 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[247] * value;

    tempvar value = (column8 - oods_values[248]) / (point - pow126 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[248] * value;

    tempvar value = (column8 - oods_values[249]) / (point - pow127 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[249] * value;

    tempvar value = (column8 - oods_values[250]) / (point - pow128 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[250] * value;

    tempvar value = (column8 - oods_values[251]) / (point - pow129 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[251] * value;

    tempvar value = (column8 - oods_values[252]) / (point - pow130 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[252] * value;

    tempvar value = (column8 - oods_values[253]) / (point - pow131 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[253] * value;

    tempvar value = (column8 - oods_values[254]) / (point - pow132 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[254] * value;

    tempvar value = (column8 - oods_values[255]) / (point - pow3 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[255] * value;

    tempvar value = (column8 - oods_values[256]) / (point - pow2 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[256] * value;

    tempvar value = (column8 - oods_values[257]) / (point - pow1 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[257] * value;

    tempvar value = (column8 - oods_values[258]) / (point - pow64 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[258] * value;

    tempvar value = (column8 - oods_values[259]) / (point - pow65 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[259] * value;

    tempvar value = (column8 - oods_values[260]) / (point - pow66 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[260] * value;

    tempvar value = (column8 - oods_values[261]) / (point - pow67 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[261] * value;

    tempvar value = (column8 - oods_values[262]) / (point - pow68 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[262] * value;

    tempvar value = (column9 - oods_values[263]) / (point - pow0 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[263] * value;

    tempvar value = (column9 - oods_values[264]) / (point - pow17 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[264] * value;

    tempvar value = (column9 - oods_values[265]) / (point - pow24 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[265] * value;

    tempvar value = (column9 - oods_values[266]) / (point - pow25 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[266] * value;

    tempvar value = (column9 - oods_values[267]) / (point - pow27 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[267] * value;

    tempvar value = (column9 - oods_values[268]) / (point - pow30 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[268] * value;

    tempvar value = (column9 - oods_values[269]) / (point - pow34 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[269] * value;

    tempvar value = (column9 - oods_values[270]) / (point - pow38 * oods_point);
    tempvar total_sum = total_sum + constraint_coefficients[270] * value;

    // Sum the OODS boundary constraints on the composition polynomials.
    let (oods_point_to_deg) = pow(oods_point, CONSTRAINT_DEGREE);

    tempvar value = (column_values[NUM_COLUMNS_FIRST + NUM_COLUMNS_SECOND] - oods_values[271]) / (
        point - oods_point_to_deg
    );
    tempvar total_sum = total_sum + constraint_coefficients[271] * value;

    tempvar value = (column_values[NUM_COLUMNS_FIRST + NUM_COLUMNS_SECOND + 1] - oods_values[272]) /
        (point - oods_point_to_deg);
    tempvar total_sum = total_sum + constraint_coefficients[272] * value;

    static_assert 273 == MASK_SIZE + CONSTRAINT_DEGREE;
    return (res=total_sum);
}
