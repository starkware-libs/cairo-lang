import dataclasses
from dataclasses import field
from typing import Any, Dict, Optional

from starkware.cairo.lang.builtins.bitwise.instance_def import BitwiseInstanceDef
from starkware.cairo.lang.builtins.ec.instance_def import EcOpInstanceDef
from starkware.cairo.lang.builtins.hash.instance_def import PedersenInstanceDef
from starkware.cairo.lang.builtins.keccak.instance_def import KeccakInstanceDef
from starkware.cairo.lang.builtins.poseidon.instance_def import PoseidonInstanceDef
from starkware.cairo.lang.builtins.range_check.instance_def import RangeCheckInstanceDef
from starkware.cairo.lang.builtins.signature.instance_def import EcdsaInstanceDef
from starkware.cairo.lang.dynamic_layout_params import DYNAMIC_LAYOUT_NAME

PRIME = 2**251 + 17 * 2**192 + 1


@dataclasses.dataclass
class CpuInstanceDef:
    # Verifies that each 'call' instruction returns, even if the called function is malicious.
    safe_call: bool = True


@dataclasses.dataclass
class DilutedPoolInstanceDef:
    # The ratio between the number of diluted cells in the pool and the number of cpu steps.
    units_per_step: int

    # In diluted form the binary sequence **** of length n_bits is represented as 00*00*00*00*,
    # with (spacing - 1) zero bits between consecutive information carying bits.
    spacing: int

    # The number of (information) bits (before diluting).
    n_bits: int


@dataclasses.dataclass
class CairoLayout:
    layout_name: str = ""
    cpu_component_step: int = 1
    # Range check units.
    rc_units: int = 16
    builtins: Dict[str, Any] = field(default_factory=lambda: {})
    # The ratio between the number of public memory cells and the total number of memory cells.
    public_memory_fraction: int = 4
    memory_units_per_step: int = 8
    diluted_pool_instance_def: Optional[DilutedPoolInstanceDef] = None
    n_trace_columns: Optional[int] = None
    cpu_instance_def: CpuInstanceDef = field(default=CpuInstanceDef())


def build_dynamic_layout(**ratios) -> CairoLayout:
    return CairoLayout(
        layout_name=DYNAMIC_LAYOUT_NAME,
        cpu_component_step=1,
        rc_units=16,
        builtins=dict(
            output=True,
            pedersen=PedersenInstanceDef(
                ratio=ratios.get("pedersen"),
                repetitions=4,
                element_height=256,
                element_bits=252,
                n_inputs=2,
                hash_limit=PRIME,
            ),
            range_check=RangeCheckInstanceDef(
                ratio=ratios.get("range_check"),
                n_parts=8,
            ),
            ecdsa=EcdsaInstanceDef(
                ratio=ratios.get("ecdsa"),
                repetitions=1,
                height=256,
                n_hash_bits=251,
            ),
            bitwise=BitwiseInstanceDef(
                ratio=ratios.get("bitwise"),
                total_n_bits=251,
            ),
            ec_op=EcOpInstanceDef(
                ratio=ratios.get("ec_op"),
                scalar_height=256,
                scalar_bits=252,
                scalar_limit=PRIME,
            ),
        ),
        public_memory_fraction=8,
        memory_units_per_step=8,
        diluted_pool_instance_def=DilutedPoolInstanceDef(
            units_per_step=16,
            spacing=4,
            n_bits=16,
        ),
        n_trace_columns=73,
    )


plain_instance = CairoLayout(
    layout_name="plain",
    n_trace_columns=8,
)

small_instance = CairoLayout(
    layout_name="small",
    rc_units=16,
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=8,
            repetitions=4,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        ecdsa=EcdsaInstanceDef(
            ratio=512,
            repetitions=1,
            height=256,
            n_hash_bits=251,
        ),
    ),
    n_trace_columns=25,
)

dex_instance = CairoLayout(
    layout_name="dex",
    rc_units=4,
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=8,
            repetitions=4,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        ecdsa=EcdsaInstanceDef(
            ratio=512,
            repetitions=1,
            height=256,
            n_hash_bits=251,
        ),
    ),
    n_trace_columns=22,
)

starknet_instance = CairoLayout(
    layout_name="starknet",
    rc_units=4,
    diluted_pool_instance_def=DilutedPoolInstanceDef(
        units_per_step=2,
        spacing=4,
        n_bits=16,
    ),
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=32,
            repetitions=1,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=16,
            n_parts=8,
        ),
        ecdsa=EcdsaInstanceDef(
            ratio=2048,
            repetitions=1,
            height=256,
            n_hash_bits=251,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=64,
            total_n_bits=251,
        ),
        ec_op=EcOpInstanceDef(
            ratio=1024,
            scalar_height=256,
            scalar_bits=252,
            scalar_limit=PRIME,
        ),
        poseidon=PoseidonInstanceDef(
            ratio=32,
            partial_rounds_partition=[64, 22],
        ),
    ),
    n_trace_columns=10,
)

starknet_with_keccak_instance = CairoLayout(
    layout_name="starknet_with_keccak",
    rc_units=4,
    diluted_pool_instance_def=DilutedPoolInstanceDef(
        units_per_step=16,
        spacing=4,
        n_bits=16,
    ),
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=32,
            repetitions=1,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=16,
            n_parts=8,
        ),
        ecdsa=EcdsaInstanceDef(
            ratio=2048,
            repetitions=1,
            height=256,
            n_hash_bits=251,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=64,
            total_n_bits=251,
        ),
        ec_op=EcOpInstanceDef(
            ratio=1024,
            scalar_height=256,
            scalar_bits=252,
            scalar_limit=PRIME,
        ),
        keccak=KeccakInstanceDef(
            ratio=2**11,
            state_rep=[200] * 8,
            instances_per_component=16,
        ),
        poseidon=PoseidonInstanceDef(
            ratio=32,
            partial_rounds_partition=[64, 22],
        ),
    ),
    n_trace_columns=15,
)

# A layout for a Cairo verification proof.
recursive_instance = CairoLayout(
    layout_name="recursive",
    rc_units=4,
    public_memory_fraction=8,
    diluted_pool_instance_def=DilutedPoolInstanceDef(
        units_per_step=16,
        spacing=4,
        n_bits=16,
    ),
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=128,
            repetitions=1,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=8,
            total_n_bits=251,
        ),
    ),
    n_trace_columns=10,
)

# A layout with a lot of bitwise and pedersen instances (e.g., for Cairo stark verification
# with long output).
recursive_large_output_instance = CairoLayout(
    layout_name="recursive_large_output",
    rc_units=4,
    public_memory_fraction=8,
    diluted_pool_instance_def=DilutedPoolInstanceDef(
        units_per_step=16,
        spacing=4,
        n_bits=16,
    ),
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=32,
            repetitions=1,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=8,
            total_n_bits=251,
        ),
    ),
    n_trace_columns=13,
)

# A layout optimized for a cairo verifier program that is being verified by a cairo verifier.
all_cairo_instance = CairoLayout(
    layout_name="all_cairo",
    rc_units=4,
    public_memory_fraction=8,
    diluted_pool_instance_def=DilutedPoolInstanceDef(
        units_per_step=16,
        spacing=4,
        n_bits=16,
    ),
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=256,
            repetitions=1,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        ecdsa=EcdsaInstanceDef(
            ratio=2048,
            repetitions=1,
            height=256,
            n_hash_bits=251,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=16,
            total_n_bits=251,
        ),
        ec_op=EcOpInstanceDef(
            ratio=1024,
            scalar_height=256,
            scalar_bits=252,
            scalar_limit=PRIME,
        ),
        keccak=KeccakInstanceDef(
            ratio=2**11,
            state_rep=[200] * 8,
            instances_per_component=16,
        ),
        poseidon=PoseidonInstanceDef(
            ratio=256,
            partial_rounds_partition=[64, 22],
        ),
    ),
    n_trace_columns=11,
)

all_solidity_instance = CairoLayout(
    layout_name="all_solidity",
    rc_units=8,
    public_memory_fraction=8,
    diluted_pool_instance_def=DilutedPoolInstanceDef(
        units_per_step=16,
        spacing=4,
        n_bits=16,
    ),
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=8,
            repetitions=4,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        ecdsa=EcdsaInstanceDef(
            ratio=512,
            repetitions=1,
            height=256,
            n_hash_bits=251,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=256,
            total_n_bits=251,
        ),
        ec_op=EcOpInstanceDef(
            ratio=256,
            scalar_height=256,
            scalar_bits=252,
            scalar_limit=PRIME,
        ),
    ),
    n_trace_columns=27,
)

LAYOUTS: Dict[str, CairoLayout] = {
    "plain": plain_instance,
    "small": small_instance,
    "dex": dex_instance,
    "recursive": recursive_instance,
    "starknet": starknet_instance,
    "recursive_large_output": recursive_large_output_instance,
    "all_solidity": all_solidity_instance,
    "starknet_with_keccak": starknet_with_keccak_instance,
}
