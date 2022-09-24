import dataclasses
from dataclasses import field
from typing import Any, Dict, Optional

from starkware.cairo.lang.builtins.bitwise.instance_def import BitwiseInstanceDef
from starkware.cairo.lang.builtins.ec.instance_def import EcOpInstanceDef
from starkware.cairo.lang.builtins.hash.instance_def import PedersenInstanceDef
from starkware.cairo.lang.builtins.keccak.instance_def import KeccakInstanceDef
from starkware.cairo.lang.builtins.range_check.instance_def import RangeCheckInstanceDef
from starkware.cairo.lang.builtins.signature.instance_def import EcdsaInstanceDef
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME

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
            hash_limit=DEFAULT_PRIME,
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
            hash_limit=DEFAULT_PRIME,
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

perpetual_with_bitwise_instance = CairoLayout(
    layout_name="perpetual_with_bitwise",
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
            hash_limit=DEFAULT_PRIME,
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
            scalar_limit=DEFAULT_PRIME,
        ),
    ),
    n_trace_columns=10,
)

# A layout with a lot of bitwise instances (e.g., for a Cairo implementation of hash functions).
bitwise_instance = CairoLayout(
    layout_name="bitwise",
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
            hash_limit=DEFAULT_PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        ecdsa=EcdsaInstanceDef(
            ratio=1024,
            repetitions=1,
            height=256,
            n_hash_bits=251,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=8,
            total_n_bits=251,
        ),
    ),
    n_trace_columns=10,
)

# A layout optimized for a cairo verifier program that is being verified by a cairo verifier.
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
            ratio=256,
            repetitions=1,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=DEFAULT_PRIME,
        ),
        range_check=RangeCheckInstanceDef(
            ratio=8,
            n_parts=8,
        ),
        bitwise=BitwiseInstanceDef(
            ratio=16,
            total_n_bits=251,
        ),
        keccak=KeccakInstanceDef(
            ratio=2**11,
            state_rep=[200] * 8,
            instances_per_component=16,
        ),
    ),
    n_trace_columns=11,
)

all_instance = CairoLayout(
    layout_name="all",
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
            hash_limit=DEFAULT_PRIME,
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
            scalar_limit=DEFAULT_PRIME,
        ),
    ),
    n_trace_columns=27,
)

LAYOUTS: Dict[str, CairoLayout] = {
    "plain": plain_instance,
    "small": small_instance,
    "dex": dex_instance,
    "bitwise": bitwise_instance,
    "perpetual_with_bitwise": perpetual_with_bitwise_instance,
    "all": all_instance,
}
