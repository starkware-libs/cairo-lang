import dataclasses
from dataclasses import field
from typing import Any, Dict

from starkware.cairo.lang.builtins.hash.instance_def import CELLS_PER_HASH, PedersenInstanceDef
from starkware.cairo.lang.builtins.range_check.instance_def import (
    CELLS_PER_RANGE_CHECK, RangeCheckInstanceDef)
from starkware.cairo.lang.builtins.signature.instance_def import (
    CELLS_PER_SIGNATURE, EcdsaInstanceDef)


@dataclasses.dataclass
class CpuInstanceDef:
    # Verifies that each 'call' instruction returns, even if the called function is malicious.
    safe_call: bool = True


@dataclasses.dataclass
class CairoLayout:
    layout_name: str = ''
    cpu_component_step: int = 1
    # Range check units.
    rc_units: int = 16
    builtins: Dict[str, Any] = field(default_factory=lambda: {})
    # The ratio between the number of public memory cells and the total number of memory cells.
    public_memory_fraction: int = 4
    memory_units_per_step: int = 8
    cpu_instance_def: CpuInstanceDef = field(default=CpuInstanceDef())


CELLS_PER_BUILTIN = dict(
    pedersen=CELLS_PER_HASH,
    range_check=CELLS_PER_RANGE_CHECK,
    ecdsa=CELLS_PER_SIGNATURE,
)

plain_instance = CairoLayout(
    layout_name='plain',
)

small_instance = CairoLayout(
    layout_name='small',
    rc_units=16,
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=8,
            repetitions=4,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=2**251 + 17 * 2**192 + 1,
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
    )
)

dex_instance = CairoLayout(
    layout_name='dex',
    rc_units=4,
    builtins=dict(
        output=True,
        pedersen=PedersenInstanceDef(
            ratio=8,
            repetitions=4,
            element_height=256,
            element_bits=252,
            n_inputs=2,
            hash_limit=2**251 + 17 * 2**192 + 1,
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
    )
)

LAYOUTS: Dict[str, CairoLayout] = {
    'plain': plain_instance,
    'small': small_instance,
    'dex': dex_instance,
}
