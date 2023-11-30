import dataclasses
from dataclasses import field
from typing import Any, Dict, Optional, Union

from starkware.cairo.lang.builtins.all_builtins import (
    OUTPUT_BUILTIN,
    SUPPORTED_DYNAMIC_BUILTINS,
    BuiltinList,
)
from starkware.cairo.lang.builtins.bitwise.instance_def import BitwiseInstanceDef
from starkware.cairo.lang.builtins.ec.instance_def import EcOpInstanceDef
from starkware.cairo.lang.builtins.hash.instance_def import PedersenInstanceDef
from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef
from starkware.cairo.lang.builtins.keccak.instance_def import KECCAK_BATCH_SIZE, KeccakInstanceDef
from starkware.cairo.lang.builtins.poseidon.instance_def import PoseidonInstanceDef
from starkware.cairo.lang.builtins.range_check.instance_def import RangeCheckInstanceDef
from starkware.cairo.lang.builtins.signature.instance_def import EcdsaInstanceDef
from starkware.python.math_utils import div_ceil, safe_div

PRIME = 2**251 + 17 * 2**192 + 1
COMPONENT_HEIGHT = 16

DYNAMIC_LAYOUT_NAME = "dynamic"


@dataclasses.dataclass
class CpuInstanceDef:
    # Verifies that each 'call' instruction returns, even if the called function is malicious.
    safe_call: bool = True


@dataclasses.dataclass
class DilutedPoolInstanceDef:
    # The log of the ratio between the number of diluted cells in the pool
    # and the number of cpu steps.
    # The case of log_units_per_step < 0 is possible when there are only few
    # builtins that require diluted units (as bitwise and keccak).
    log_units_per_step: Optional[int]

    # In diluted form the binary sequence **** of length n_bits is represented as 00*00*00*00*,
    # with (spacing - 1) zero bits between consecutive information carying bits.
    spacing: int

    # The number of (information) bits (before diluting).
    n_bits: int


@dataclasses.dataclass
class BuiltinsInfo:
    output: bool = field(default=True)
    # Dictionary of builtin definitions. Note that builtin definitions only exist for builtins that
    # are implemented with a periodic constraint in the trace, i.e., all builtins except for the
    # output builtin. Therefore, the output builtin is not included in this dictionary.
    builtin_defs: Dict[str, BuiltinInstanceDef] = field(default_factory=lambda: {})

    @property
    def builtins_list(self) -> BuiltinList:
        list_of_builtins = []
        if self.output:
            list_of_builtins.append(OUTPUT_BUILTIN)
        list_of_builtins.extend(self.builtin_defs.keys())

        return BuiltinList(list_of_builtins)


@dataclasses.dataclass
class CairoLayout:
    layout_name: str = ""
    cpu_component_step: Optional[int] = 1
    # Range check units.
    rc_units: Optional[int] = 16
    builtins: Dict[str, Any] = field(default_factory=lambda: {})
    # The ratio between the number of public memory cells and the total number of memory cells.
    public_memory_fraction: int = 4
    memory_units_per_step: Optional[int] = 8
    diluted_pool_instance_def: Optional[DilutedPoolInstanceDef] = None
    n_trace_columns: Optional[int] = None
    cpu_instance_def: CpuInstanceDef = field(default=CpuInstanceDef())

    @property
    def diluted_units_row_ratio(self) -> Optional[int]:
        assert self.diluted_pool_instance_def is not None
        log_units_per_step = self.diluted_pool_instance_def.log_units_per_step
        assert log_units_per_step is not None
        assert self.cpu_component_step is not None
        if log_units_per_step >= 0:
            return safe_div(COMPONENT_HEIGHT * self.cpu_component_step, 2**log_units_per_step)
        return COMPONENT_HEIGHT * self.cpu_component_step * 2**-log_units_per_step


def build_builtins_dict_with_default_params(
    **ratios: Optional[int],
) -> Dict[str, Union[BuiltinInstanceDef, bool]]:
    """
    Creates a builtins dictionary according to the given ratios.
    The ratios are allowed to be None - this is used when constructing the AIR before knowing the
    ratios.
    """
    assert all(builtin in SUPPORTED_DYNAMIC_BUILTINS for builtin in ratios.keys())
    builtin_dict: Dict[str, Union[BuiltinInstanceDef, bool]] = {"output": True}
    builtin_dict["pedersen"] = PedersenInstanceDef(
        ratio=ratios.get("pedersen"),
        repetitions=1,
        element_height=256,
        element_bits=252,
        n_inputs=2,
        hash_limit=PRIME,
    )
    builtin_dict["range_check"] = RangeCheckInstanceDef(
        ratio=ratios.get("range_check"),
        n_parts=8,
    )
    builtin_dict["ecdsa"] = EcdsaInstanceDef(
        ratio=ratios.get("ecdsa"),
        repetitions=1,
        height=256,
        n_hash_bits=251,
    )
    builtin_dict["bitwise"] = BitwiseInstanceDef(
        ratio=ratios.get("bitwise"),
        total_n_bits=251,
    )
    builtin_dict["ec_op"] = EcOpInstanceDef(
        ratio=ratios.get("ec_op"),
        scalar_height=256,
        scalar_bits=252,
        scalar_limit=PRIME,
    )
    builtin_dict["keccak"] = KeccakInstanceDef(
        ratio=ratios.get("keccak"),
        state_rep=[200] * 8,
        instances_per_component=16,
    )
    builtin_dict["poseidon"] = PoseidonInstanceDef(
        ratio=ratios.get("poseidon"),
        partial_rounds_partition=[64, 22],
    )

    return builtin_dict


BATCH_SIZES: Dict[str, int] = {
    "keccak": KECCAK_BATCH_SIZE,
}


def get_implemented_size_per_builtin(builtin_name: str, requested_usage: int = 0) -> int:
    batch_size = BATCH_SIZES.get(builtin_name, 1)
    return batch_size * div_ceil(requested_usage, batch_size)


DYNAMIC_DILUTED_SPACING = 4
DYNAMIC_DILUTED_N_BITS = 16
DYNAMIC_PUBLIC_MEMORY_FRACTION = 8


def build_dynamic_layout(
    log_diluted_units_per_step: Optional[int] = None,
    cpu_component_step: Optional[int] = None,
    rc_units: Optional[int] = None,
    memory_units_per_step: Optional[int] = None,
    **ratios: Optional[int],
) -> CairoLayout:
    if len(ratios) != 0:
        for builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN):
            if builtin_name not in ratios:
                ratios[builtin_name] = 0

    return CairoLayout(
        layout_name=DYNAMIC_LAYOUT_NAME,
        cpu_component_step=cpu_component_step,
        rc_units=rc_units,
        builtins=build_builtins_dict_with_default_params(**ratios),
        public_memory_fraction=DYNAMIC_PUBLIC_MEMORY_FRACTION,
        memory_units_per_step=memory_units_per_step,
        diluted_pool_instance_def=DilutedPoolInstanceDef(
            log_units_per_step=log_diluted_units_per_step,
            spacing=DYNAMIC_DILUTED_SPACING,
            n_bits=DYNAMIC_DILUTED_N_BITS,
        ),
        n_trace_columns=None,
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
        log_units_per_step=1,
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
        log_units_per_step=4,
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
        log_units_per_step=4,
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
        log_units_per_step=4,
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
        log_units_per_step=4,
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
        log_units_per_step=4,
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
    "dynamic": build_dynamic_layout(),
}
