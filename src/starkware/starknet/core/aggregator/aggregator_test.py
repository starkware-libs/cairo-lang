import os
from enum import Enum, auto
from typing import List, Optional, Tuple

import pytest

from starkware.cairo.bootloaders.fact_topology import (
    FactTopology,
    get_fact_topology_from_additional_data,
)
from starkware.cairo.bootloaders.generate_fact import get_aggregator_input_size
from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.poseidon_hash import poseidon_hash, poseidon_hash_many
from starkware.cairo.common.validate_utils import validate_builtin_usage
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.vm.vm_exceptions import VmException
from starkware.python.test_utils import maybe_raises
from starkware.starknet.core.aggregator.output_parser import (
    ContractChanges,
    OsOutput,
    TaskOutput,
    parse_bootloader_output,
)
from starkware.starknet.core.aggregator.utils import OsOutputToCairo

# Dummy values for the test.
OS_PROGRAM_HASH = 0x7E0B89C77D0003C05511B9F0E1416F1328C2132E41E056B2EF3BC950135360F
OS_CONFIG_HASH = 0x3410F9DCE5078BFA24B30F28F9F9107A995E5F339334A7126730A993045681
BLOCK0_HASH = 0x1C5CA4BCC4C03D843B8C08F9C8628BA7A108D2B62F4C0F6EF224F250679230E
BLOCK1_HASH = 0x378294C261592B32272381910BCB2402A864E1CDF68EDC855CAA24CACF68B65
ROOT0 = 0
ROOT1 = 0x3BCBB6FD22F39E772ACE7F905AC64FBF6D7139CAC2C44189D59B37618BB62D0
ROOT2 = 0x269DDFB6E729A030E3513A7E8208D68BE9AB97852681FB531E7FC69FAC2852A

CONTRACT_ADDR0 = 0x2E9D5D85CEA6989999E86023CAD0B578825667C4DB413F3DAC8B4569A209F01
CONTRACT_ADDR1 = 0x3BBF5259540526B676273C9BE35F79DA62B07F0EDD0FD3E80F8BD1CE9F4A460
CONTRACT_ADDR2 = 0x42593E24F58291B1D7E4FD081AE6DD88D0B198E23C3F722E7E5A7A4C7BCD3D5
CLASS_HASH0_0 = 0x178286A1179F01D8A55F34B8CC651C7DD7B298B222A392197E703C3F8E161DE
CLASS_HASH0_1 = 0x39AB5549FE5E57DA8C8581AE51A0E42D9A15296BFF9BD3D7513A769CF20F7E3
CLASS_HASH1_0 = 0x55791A41352DE2EDC137AF1A2C68B9037267538FCA5119749E76430023CB01A
CLASS_HASH1_1 = 0x3676FAA37D4816933AC54BD1D90E230DB0BBB43F108CDF51555584D69A43A82
CLASS_HASH2_0 = 0x6D2819C30302763858FEC692B69ED9C9B51C4B0973F8EF8B947FF08F3D671BD
STORAGE_KEY0 = 0x0B6CE5410FCA59D078EE9B2A4371A9D684C530D697C64FBEF0AE6D5E8F0AC72
STORAGE_KEY1 = 0x110E2F729C9C2B988559994A3DACCD838CF52FAF88E18101373E67DD061455A
STORAGE_KEY2 = 0x1390569BB0A3A722EB4228E8700301347DA081211D5C2DED2DB22EF389551AB
STORAGE_KEY3 = 0x1024A17A64F318C191BAB4FEEEDA0A65B420FF92861FFB021759F05A2598ABF
STORAGE_KEY4 = 0x7C53010B8E69908E662971B823582B951E5B8E85A557C4BD3B0666428C3E520

STORAGE_VALUE0_0 = 0x346C2C2E73F8E0D5C1F3C9E2DB1CCA9B2315AD0857C4F26B076554BA4095558
STORAGE_VALUE0_1 = 0x15A44BFBB65C4961F54BC84CADBFC542AA8529E293E9FD7D45E3008DD75F376
STORAGE_VALUE0_2 = 0x31F90D664D5604B8B38C9C442B005B7E41BDA662E6E15A7364220D633153F35
STORAGE_VALUE1_0 = 0x141BF4A595FFC14E970EA6BE186A9462E20DCFBD7782E03AAEF08E9539B82D1
STORAGE_VALUE1_1 = 0x2456E7A60B3AB8B28E9AB0D9FBF0D437CCDDC9776664AF33FFD6506FC1AB8E1
STORAGE_VALUE2_0 = 0x0
STORAGE_VALUE2_1 = 0x20E9DCD4DDB159970BD2D51075C8CC823E68BB04777FABB65879E0EA455AEE1
STORAGE_VALUE3_0 = 0x246444B2DD74265D4273FF3E41356D82B9E9A40212AE11A33C6A5EEDD2963A4
STORAGE_VALUE3_2 = 0x3C87090C322CC7E56F05DA6AEE18B28F8DD98A787F5280BD9469B00E08AFC43
STORAGE_VALUE4_0 = 0x34F56302DB42AD3B7BEC08E6CB3F786684A20143BD623419F23FDCFD29FC1D1
STORAGE_VALUE4_2 = 0x6159FC48B5236D772E81DDB785BB9FC60D97308AFFB21FEFAD8E90DDF280BC2

COMPILED_CLASS_HASH0_0 = 0x2E2D36CD2DEFEC6CF7E095CB3186F8C5025233DC7A12B26A9EBEDBC1ACC15FD
COMPILED_CLASS_HASH0_1 = 0x1B934F1068AF398C685BF2D5A9083F7817485F2356DDF6CECF25C8085DADA96
COMPILED_CLASS_HASH0_2 = 0x207385E0C41F9BF8E0616781859A6D203CEC08B4C0CBB7087C3D8FBE8BBCC2F
COMPILED_CLASS_HASH1_0 = 0x171ADCCA37ECFD43E362AA7F5EBF94AD81A38043B946D5BEDAFAB4021567B61
COMPILED_CLASS_HASH1_1 = 0x5074A78E83098D3EC8B08A2965B1C98681AF16DF9DA04A8015DBD8BAFA8C939

MSG_TO_L1_0 = [
    0x3F9A3CD755E1C8D50080AE5C76CACB1C6CACDCDF1C467C9F0A0ABDB684A6E3D,
    0x3795FD47F065CF5541F0EA7D9702450F09898EF7,
    2,
    12,
    34,
]
MSG_TO_L1_1 = [
    0x3F9A3CD755E1C8D50080AE5C76CACB1C6CACDCDF1C467C9F0A0ABDB684A6E3D,
    0x3795FD47F065CF5541F0EA7D9702450F09898EF7,
    0,
]

MSG_TO_L2_0 = [
    0x3795FD47F065CF5541F0EA7D9702450F09898EF7,
    0x3F9A3CD755E1C8D50080AE5C76CACB1C6CACDCDF1C467C9F0A0ABDB684A6E3D,
    2,
    0,
    1,
    0x1234,
]
MSG_TO_L2_1 = [
    0x3795FD47F065CF5541F0EA7D9702450F09898EF7,
    0x3F9A3CD755E1C8D50080AE5C76CACB1C6CACDCDF1C467C9F0A0ABDB684A6E3D,
    0,
    0x4321,
]

MOCK_COMMITMENT = 0x1234, 0x5678

AGGREGATOR_COMPILED_PATH = os.path.join(os.path.dirname(__file__), "aggregator.json")


@pytest.fixture(scope="session")
def aggregator_program() -> Program:
    return Program.loads(data=open(AGGREGATOR_COMPILED_PATH).read())


def contract_header_packed_word(
    n_updates: int, prev_nonce: int, new_nonce: int, class_updated: int, full_output: bool
) -> int:
    """
    Returns the second word of the contract header.
    """
    if full_output:
        return n_updates + prev_nonce * 2**64 + new_nonce * 2**128 + class_updated * 2**192
    else:
        return n_updates + new_nonce * 2**64 + class_updated * 2**128


class FailureModifier(Enum):
    NONE = 0
    ROOT = auto()
    BLOCK_HASH = auto()
    BLOCK_NUMBER = auto()
    PROGRAM_HASH = auto()
    OS_CONFIG_HASH = auto()
    STORAGE_VALUE = auto()
    COMPILED_CLASS_HASH = auto()


def block0_output(full_output: bool):
    res = [
        # initial_root.
        ROOT0,
        # final_root.
        ROOT1,
        # Previous block number.
        0,
        # New block_number.
        1,
        # Previous block hash.
        0,
        # New block hash.
        BLOCK0_HASH,
        # OS program hash.
        0,
        OS_CONFIG_HASH,
        # use_kzg_da.
        0,
        # full_output.
        1 if full_output else 0,
        # Messages to L1.
        len(MSG_TO_L1_0),
        *MSG_TO_L1_0,
        # Messages to L2.
        len(MSG_TO_L2_0),
        *MSG_TO_L2_0,
        # Number of contracts.
        2,
        # Contract addr.
        CONTRACT_ADDR0,
        contract_header_packed_word(
            n_updates=3, prev_nonce=0, new_nonce=1, class_updated=1, full_output=full_output
        ),
        # Class hash.
        CLASS_HASH0_0 if full_output else None,
        CLASS_HASH0_1,
        # Storage updates.
        STORAGE_KEY0,
        STORAGE_VALUE0_0 if full_output else None,
        STORAGE_VALUE0_1,
        STORAGE_KEY1,
        STORAGE_VALUE1_0 if full_output else None,
        STORAGE_VALUE1_1,
        STORAGE_KEY2,
        STORAGE_VALUE2_0 if full_output else None,
        STORAGE_VALUE2_1,
        # Contract whose block0 changes are fully reverted by block1.
        # Contract addr.
        CONTRACT_ADDR1,
        contract_header_packed_word(
            n_updates=1, prev_nonce=10, new_nonce=10, class_updated=1, full_output=full_output
        ),
        # Class hash.
        CLASS_HASH1_0 if full_output else None,
        CLASS_HASH1_1,
        # Storage updates.
        STORAGE_KEY0,
        STORAGE_VALUE0_0 if full_output else None,
        STORAGE_VALUE0_1,
        # Number of classes.
        2,
        # Class updates.
        CLASS_HASH0_0,
        COMPILED_CLASS_HASH0_0 if full_output else None,
        COMPILED_CLASS_HASH0_1,
        CLASS_HASH1_0,
        COMPILED_CLASS_HASH1_0 if full_output else None,
        COMPILED_CLASS_HASH1_1,
    ]
    return [x for x in res if x is not None]


def block1_output(full_output: bool, modifier: FailureModifier = FailureModifier.NONE):
    maybe_wrong = lambda x, modifier0: x + (10 if modifier == modifier0 else 0)
    res = [
        # initial_root.
        maybe_wrong(ROOT1, FailureModifier.ROOT),
        # final_root.
        ROOT2,
        # Previous block number.
        maybe_wrong(1, FailureModifier.BLOCK_NUMBER),
        # New block_number.
        2,
        # Previous block hash.
        maybe_wrong(BLOCK0_HASH, FailureModifier.BLOCK_HASH),
        # New block hash.
        BLOCK1_HASH,
        # OS program hash.
        maybe_wrong(0, FailureModifier.PROGRAM_HASH),
        maybe_wrong(OS_CONFIG_HASH, FailureModifier.OS_CONFIG_HASH),
        # use_kzg_da.
        0,
        # full_output.
        1 if full_output else 0,
        # Messages to L1.
        len(MSG_TO_L1_1),
        *MSG_TO_L1_1,
        # Messages to L2.
        len(MSG_TO_L2_1),
        *MSG_TO_L2_1,
        # Number of contracts.
        3,
        # Contract addr.
        CONTRACT_ADDR0,
        contract_header_packed_word(
            n_updates=2, prev_nonce=1, new_nonce=2, class_updated=0, full_output=full_output
        ),
        # Class hash.
        CLASS_HASH0_1 if full_output else None,
        CLASS_HASH0_1 if full_output else None,
        # Storage updates.
        STORAGE_KEY0,
        maybe_wrong(STORAGE_VALUE0_1, FailureModifier.STORAGE_VALUE) if full_output else None,
        STORAGE_VALUE0_2,
        STORAGE_KEY3,
        STORAGE_VALUE3_0 if full_output else None,
        STORAGE_VALUE3_2,
        # Contract whose block0 changes are fully reverted by block1.
        # Contract addr.
        CONTRACT_ADDR1,
        contract_header_packed_word(
            n_updates=1, prev_nonce=10, new_nonce=10, class_updated=1, full_output=full_output
        ),
        # Class hash.
        CLASS_HASH1_1 if full_output else None,
        CLASS_HASH1_0,
        # Storage updates.
        STORAGE_KEY0,
        STORAGE_VALUE0_1 if full_output else None,
        STORAGE_VALUE0_0,
        # Contract that only appears in this block (block1).
        # Contract addr.
        CONTRACT_ADDR2,
        contract_header_packed_word(
            n_updates=1, prev_nonce=7, new_nonce=8, class_updated=0, full_output=full_output
        ),
        # Class hash.
        CLASS_HASH2_0 if full_output else None,
        CLASS_HASH2_0 if full_output else None,
        # Storage updates.
        STORAGE_KEY4,
        STORAGE_VALUE4_0 if full_output else None,
        STORAGE_VALUE4_2,
        # Number of classes.
        1,
        CLASS_HASH0_0,
        (
            maybe_wrong(COMPILED_CLASS_HASH0_1, FailureModifier.COMPILED_CLASS_HASH)
            if full_output
            else None
        ),
        COMPILED_CLASS_HASH0_2,
    ]
    return [x for x in res if x is not None]


def combined_output(full_output: bool, use_kzg_da: bool = False):
    da = combined_output_da(full_output=full_output)
    res = [
        # initial_root.
        ROOT0,
        # final_root.
        ROOT2,
        # Previous block number.
        0,
        # New block_number.
        2,
        # Previous block hash.
        0,
        # New block hash.
        BLOCK1_HASH,
        OS_PROGRAM_HASH,
        OS_CONFIG_HASH,
        # use_kzg_da.
        1 if use_kzg_da else 0,
        # full_output.
        1 if full_output else 0,
        # KZG info.
        *(combined_kzg_info(da) if use_kzg_da else []),
        # Messages to L1.
        len(MSG_TO_L1_0) + len(MSG_TO_L1_1),
        *MSG_TO_L1_0,
        *MSG_TO_L1_1,
        # Messages to L2.
        len(MSG_TO_L2_0) + len(MSG_TO_L2_1),
        *MSG_TO_L2_0,
        *MSG_TO_L2_1,
        *([] if use_kzg_da else da),
    ]
    return [x for x in res if x is not None]


def combined_output_da(full_output: bool):
    res = [
        # Number of contracts.
        3 if full_output else 2,
        # Contract addr.
        CONTRACT_ADDR0,
        contract_header_packed_word(
            n_updates=4, prev_nonce=0, new_nonce=2, class_updated=1, full_output=full_output
        ),
        # Class hash.
        CLASS_HASH0_0 if full_output else None,
        CLASS_HASH0_1,
        # Storage updates.
        STORAGE_KEY0,
        STORAGE_VALUE0_0 if full_output else None,
        STORAGE_VALUE0_2,
        STORAGE_KEY3,
        STORAGE_VALUE3_0 if full_output else None,
        STORAGE_VALUE3_2,
        STORAGE_KEY1,
        STORAGE_VALUE1_0 if full_output else None,
        STORAGE_VALUE1_1,
        STORAGE_KEY2,
        STORAGE_VALUE2_0 if full_output else None,
        STORAGE_VALUE2_1,
        # Contract addr.
        CONTRACT_ADDR1 if full_output else None,
        (
            contract_header_packed_word(
                n_updates=0, prev_nonce=10, new_nonce=10, class_updated=0, full_output=full_output
            )
            if full_output
            else None
        ),
        # Class hash.
        CLASS_HASH1_0 if full_output else None,
        CLASS_HASH1_0 if full_output else None,
        # Contract addr.
        CONTRACT_ADDR2,
        contract_header_packed_word(
            n_updates=1, prev_nonce=7, new_nonce=8, class_updated=0, full_output=full_output
        ),
        # Class hash.
        CLASS_HASH2_0 if full_output else None,
        CLASS_HASH2_0 if full_output else None,
        # Storage updates.
        STORAGE_KEY4,
        STORAGE_VALUE4_0 if full_output else None,
        STORAGE_VALUE4_2,
        # Number of classes.
        2,
        # Class updates.
        CLASS_HASH0_0,
        COMPILED_CLASS_HASH0_0 if full_output else None,
        COMPILED_CLASS_HASH0_2,
        CLASS_HASH1_0,
        COMPILED_CLASS_HASH1_0 if full_output else None,
        COMPILED_CLASS_HASH1_1,
    ]
    return [x for x in res if x is not None]


def combined_kzg_info(da: List[int]) -> List[int]:
    n_blobs = 1
    z = poseidon_hash(poseidon_hash_many(da), poseidon_hash_many(MOCK_COMMITMENT))
    BLS_PRIME = 52435875175126190479447740508185965837690552500527637822603658699938581184513
    evaluation = sum(pow(z, i, BLS_PRIME) * x for i, x in enumerate(da)) % BLS_PRIME
    evaluation_high, evaluation_low = divmod(evaluation, 2**128)

    return [z, n_blobs, *MOCK_COMMITMENT, evaluation_low, evaluation_high]


def bootloader_output(full_output: bool, modifier: FailureModifier = FailureModifier.NONE):
    block0 = block0_output(full_output=full_output)
    block1 = block1_output(full_output=full_output, modifier=modifier)
    return [
        # Number of blocks.
        2,
        len(block0) + 2,
        OS_PROGRAM_HASH,
        *block0,
        len(block1) + 2,
        OS_PROGRAM_HASH,
        *block1,
    ]


@pytest.mark.parametrize("full_output", [False, True])
def test_output_parser(full_output: bool):
    assert parse_bootloader_output(output=bootloader_output(full_output=full_output)) == [
        TaskOutput(
            program_hash=OS_PROGRAM_HASH,
            os_output=OsOutput(
                initial_root=ROOT0,
                final_root=ROOT1,
                prev_block_number=0,
                new_block_number=1,
                prev_block_hash=0,
                new_block_hash=BLOCK0_HASH,
                os_program_hash=0,
                starknet_os_config_hash=OS_CONFIG_HASH,
                use_kzg_da=0,
                full_output=1 if full_output else 0,
                messages_to_l1=MSG_TO_L1_0,
                messages_to_l2=MSG_TO_L2_0,
                contracts=[
                    ContractChanges(
                        addr=CONTRACT_ADDR0,
                        prev_nonce=0 if full_output else None,
                        new_nonce=1,
                        prev_class_hash=CLASS_HASH0_0 if full_output else None,
                        new_class_hash=CLASS_HASH0_1,
                        storage_changes={
                            STORAGE_KEY0: (
                                STORAGE_VALUE0_0 if full_output else None,
                                STORAGE_VALUE0_1,
                            ),
                            STORAGE_KEY1: (
                                STORAGE_VALUE1_0 if full_output else None,
                                STORAGE_VALUE1_1,
                            ),
                            STORAGE_KEY2: (
                                STORAGE_VALUE2_0 if full_output else None,
                                STORAGE_VALUE2_1,
                            ),
                        },
                    ),
                    ContractChanges(
                        addr=CONTRACT_ADDR1,
                        prev_nonce=10 if full_output else None,
                        new_nonce=10,
                        prev_class_hash=CLASS_HASH1_0 if full_output else None,
                        new_class_hash=CLASS_HASH1_1,
                        storage_changes={
                            STORAGE_KEY0: (
                                STORAGE_VALUE0_0 if full_output else None,
                                STORAGE_VALUE0_1,
                            ),
                        },
                    ),
                ],
                classes={
                    CLASS_HASH0_0: (
                        COMPILED_CLASS_HASH0_0 if full_output else None,
                        COMPILED_CLASS_HASH0_1,
                    ),
                    CLASS_HASH1_0: (
                        COMPILED_CLASS_HASH1_0 if full_output else None,
                        COMPILED_CLASS_HASH1_1,
                    ),
                },
            ),
        ),
        TaskOutput(
            program_hash=OS_PROGRAM_HASH,
            os_output=OsOutput(
                initial_root=ROOT1,
                final_root=ROOT2,
                prev_block_number=1,
                new_block_number=2,
                prev_block_hash=BLOCK0_HASH,
                new_block_hash=BLOCK1_HASH,
                os_program_hash=0,
                starknet_os_config_hash=OS_CONFIG_HASH,
                use_kzg_da=0,
                full_output=1 if full_output else 0,
                messages_to_l1=MSG_TO_L1_1,
                messages_to_l2=MSG_TO_L2_1,
                contracts=[
                    ContractChanges(
                        addr=CONTRACT_ADDR0,
                        prev_nonce=1 if full_output else None,
                        new_nonce=2,
                        prev_class_hash=CLASS_HASH0_1 if full_output else None,
                        new_class_hash=CLASS_HASH0_1 if full_output else None,
                        storage_changes={
                            STORAGE_KEY0: (
                                STORAGE_VALUE0_1 if full_output else None,
                                STORAGE_VALUE0_2,
                            ),
                            STORAGE_KEY3: (
                                STORAGE_VALUE3_0 if full_output else None,
                                STORAGE_VALUE3_2,
                            ),
                        },
                    ),
                    ContractChanges(
                        addr=CONTRACT_ADDR1,
                        prev_nonce=10 if full_output else None,
                        new_nonce=10,
                        prev_class_hash=CLASS_HASH1_1 if full_output else None,
                        new_class_hash=CLASS_HASH1_0,
                        storage_changes={
                            STORAGE_KEY0: (
                                STORAGE_VALUE0_1 if full_output else None,
                                STORAGE_VALUE0_0,
                            ),
                        },
                    ),
                    ContractChanges(
                        addr=CONTRACT_ADDR2,
                        prev_nonce=7 if full_output else None,
                        new_nonce=8,
                        prev_class_hash=CLASS_HASH2_0 if full_output else None,
                        new_class_hash=CLASS_HASH2_0 if full_output else None,
                        storage_changes={
                            STORAGE_KEY4: (
                                STORAGE_VALUE4_0 if full_output else None,
                                STORAGE_VALUE4_2,
                            ),
                        },
                    ),
                ],
                classes={
                    CLASS_HASH0_0: (
                        COMPILED_CLASS_HASH0_1 if full_output else None,
                        COMPILED_CLASS_HASH0_2,
                    ),
                },
            ),
        ),
    ]


@pytest.mark.parametrize("block_idx", [0, 1])
@pytest.mark.parametrize("full_output_result", [False, True])
def test_parse_and_output(aggregator_program, block_idx: int, full_output_result: bool):
    runner = CairoFunctionRunner(aggregator_program, layout="recursive_with_poseidon")
    os_output_segment = runner.segments.add()

    os_output = parse_bootloader_output(output=bootloader_output(full_output=True))[
        block_idx
    ].os_output
    os_output.full_output = 1 if full_output_result else 0
    OsOutputToCairo(runner.segments).process_os_output(
        segments=runner.segments, dst_ptr=os_output_segment, os_output=os_output
    )

    runner.run(
        "serialize_os_output",
        range_check_ptr=runner.range_check_builtin.base,
        poseidon_ptr=runner.poseidon_builtin.base,
        output_ptr=runner.output_builtin.base,
        os_output=os_output_segment,
        hint_locals=dict(__serialize_data_availability_create_pages__=False),
    )

    range_check_end, poseidon_end, output_builtin_end = runner.get_return_values(3)

    validate_builtin_usage(builtin_runner=runner.range_check_builtin, end_ptr=range_check_end)
    validate_builtin_usage(builtin_runner=runner.poseidon_builtin, end_ptr=poseidon_end)
    res = runner.memory.get_range(
        runner.output_builtin.base, output_builtin_end - runner.output_builtin.base
    )
    if block_idx == 0:
        assert res == block0_output(full_output=full_output_result)
    else:
        assert res == block1_output(full_output=full_output_result)


def mock_polynomial_coefficients_to_kzg_commitment(coefficients: List[int]) -> Tuple[int, int]:
    return MOCK_COMMITMENT


@pytest.mark.parametrize(
    "full_output, use_kzg_da, modifier, error_message",
    [
        (False, False, FailureModifier.NONE, None),
        (True, False, FailureModifier.NONE, None),
        (False, True, FailureModifier.NONE, None),
        (True, True, FailureModifier.NONE, None),
        (True, False, FailureModifier.ROOT, f"{ROOT1} != {ROOT1 + 10}"),
        (True, False, FailureModifier.BLOCK_HASH, f"{BLOCK0_HASH} != {BLOCK0_HASH + 10}"),
        (True, False, FailureModifier.BLOCK_NUMBER, f"1 != 11"),
        (True, False, FailureModifier.PROGRAM_HASH, f"0 != 10"),
        (True, False, FailureModifier.OS_CONFIG_HASH, f"{OS_CONFIG_HASH} != {OS_CONFIG_HASH + 10}"),
        (
            True,
            False,
            FailureModifier.STORAGE_VALUE,
            f"{STORAGE_VALUE0_1} != {STORAGE_VALUE0_1 + 10}",
        ),
        (
            True,
            False,
            FailureModifier.COMPILED_CLASS_HASH,
            f"{COMPILED_CLASS_HASH0_1} != {COMPILED_CLASS_HASH0_1 + 10}",
        ),
    ],
)
def test_aggregator(
    aggregator_program: Program,
    full_output: bool,
    use_kzg_da: bool,
    modifier: FailureModifier,
    error_message: Optional[str],
):
    runner = CairoFunctionRunner(aggregator_program, layout="recursive_with_poseidon")

    bootloader_output_data = bootloader_output(full_output=True, modifier=modifier)
    hint_locals = {
        "program_input": {
            "bootloader_output": bootloader_output_data,
            "use_kzg_da": use_kzg_da,
            "full_output": full_output,
        },
        "polynomial_coefficients_to_kzg_commitment_callback": (
            mock_polynomial_coefficients_to_kzg_commitment
        ),
    }

    with maybe_raises(VmException, error_message=error_message):
        runner.run(
            "main",
            output_ptr=runner.output_builtin.base,
            range_check_ptr=runner.range_check_builtin.base,
            poseidon_ptr=runner.poseidon_builtin.base,
            hint_locals=hint_locals,
        )
        output_builtin_end, range_check_end, poseidon_end = runner.get_return_values(3)

    if error_message is not None:
        return

    validate_builtin_usage(builtin_runner=runner.range_check_builtin, end_ptr=range_check_end)
    validate_builtin_usage(builtin_runner=runner.poseidon_builtin, end_ptr=poseidon_end)
    res = runner.memory.get_range(
        runner.output_builtin.base, output_builtin_end - runner.output_builtin.base
    )
    combined_output_ = combined_output(full_output=full_output, use_kzg_da=use_kzg_da)
    assert res == bootloader_output_data + combined_output_

    # Test fact topology.
    fact_topology = get_fact_topology_from_additional_data(
        output_size=len(res),
        output_builtin_additional_data=runner.output_builtin.get_additional_data(),
    )
    if use_kzg_da:
        assert fact_topology == FactTopology.trivial(
            page0_size=len(bootloader_output_data) + len(combined_output_)
        )
    else:
        da_len = len(combined_output_da(full_output=full_output))
        len_without_da = len(bootloader_output_data) + len(combined_output_) - da_len
        assert fact_topology == FactTopology(
            tree_structure=[2, 1, 0, 2], page_sizes=[len_without_da, da_len]
        )


def test_get_aggregator_input_size():
    # The bootloader output is the input of the aggregator.
    bootloader_output_data = bootloader_output(full_output=True)
    assert get_aggregator_input_size(
        bootloader_output_data + combined_output(full_output=True)
    ) == len(bootloader_output_data)
