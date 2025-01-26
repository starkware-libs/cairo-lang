import dataclasses
from fractions import Fraction
from typing import Dict, Optional

from starkware.cairo.lang.builtins.all_builtins import (
    LOW_RATIO_BUILTINS,
    OUTPUT_BUILTIN,
    SUPPORTED_DYNAMIC_BUILTINS,
)
from starkware.cairo.lang.builtins.instance_def import (
    BuiltinInstanceDef,
    BuiltinInstanceDefWithLowRatio,
)
from starkware.cairo.lang.instances import COMPONENT_HEIGHT, CairoLayout, build_dynamic_layout
from starkware.python.math_utils import safe_div, safe_log2

MAX_CPU_COMPONENT_STEP = 2**8
MIN_MEMORY_UNITS_PER_STEP = 4
NUM_COLUMNS_FIRST_BOUND = 2**16
NUM_COLUMNS_SECOND_BOUND = 2**16

ROW_RATIO_NAMES = {
    "pedersen": "pedersen_builtin_row_ratio",
    "range_check": "range_check_builtin_row_ratio",
    "ecdsa": "ecdsa_builtin_row_ratio",
    "bitwise": "bitwise__row_ratio",
    "ec_op": "ec_op_builtin_row_ratio",
    "keccak": "keccak__row_ratio",
    "poseidon": "poseidon__row_ratio",
    "range_check96": "range_check96_builtin_row_ratio",
    "add_mod": "add_mod__row_ratio",
    "mul_mod": "mul_mod__row_ratio",
}


@dataclasses.dataclass(frozen=True)
class CairoLayoutParams:
    """
    Configurable parameters for a dynamic Cairo layout. Can be used to serialize/deserialize dynamic
    CairoLayout objects more easily (since it only contains the configurable parameters).
    """

    cpu_component_step: int
    rc_units: int
    memory_units_per_step: int
    log_diluted_units_per_step: int
    uses_pedersen_builtin: int
    pedersen_ratio: int
    uses_range_check_builtin: int
    range_check_ratio: int
    uses_ecdsa_builtin: int
    ecdsa_ratio: int
    uses_bitwise_builtin: int
    bitwise_ratio: int
    uses_ec_op_builtin: int
    ec_op_ratio: int
    uses_keccak_builtin: int
    keccak_ratio: int
    uses_poseidon_builtin: int
    poseidon_ratio: int
    uses_range_check96_builtin: int
    range_check96_ratio: int
    range_check96_ratio_den: int
    uses_add_mod_builtin: int
    add_mod_ratio: int
    add_mod_ratio_den: int
    uses_mul_mod_builtin: int
    mul_mod_ratio: int
    mul_mod_ratio_den: int

    @property
    def diluted_units_row_ratio(self) -> Optional[int]:
        if self.log_diluted_units_per_step >= 0:
            return safe_div(
                COMPONENT_HEIGHT * self.cpu_component_step, 2**self.log_diluted_units_per_step
            )
        return COMPONENT_HEIGHT * self.cpu_component_step * 2**-self.log_diluted_units_per_step

    def __post_init__(self):
        for builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN):
            if self.get_uses_builtin(builtin_name) == 0:
                assert self.get_builtin_ratio(builtin_name) == 0

    @staticmethod
    def create_from_cairo_layout(cairo_layout: CairoLayout) -> "CairoLayoutParams":
        assert cairo_layout.diluted_pool_instance_def is not None
        assert cairo_layout.cpu_component_step is not None
        assert cairo_layout.rc_units is not None
        assert cairo_layout.memory_units_per_step is not None
        assert cairo_layout.diluted_pool_instance_def.log_units_per_step is not None

        builtins_params_dict: Dict[str, int] = {}
        for builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN):
            assert builtin_name in cairo_layout.builtins
            builtin = cairo_layout.builtins[builtin_name]
            assert isinstance(builtin, BuiltinInstanceDef)
            assert builtin.ratio is not None
            if builtin.is_used():
                builtins_params_dict[f"uses_{builtin_name}_builtin"] = 1
                builtins_params_dict[f"{builtin_name}_ratio"] = builtin.ratio
            else:
                builtins_params_dict[f"uses_{builtin_name}_builtin"] = 0
                builtins_params_dict[f"{builtin_name}_ratio"] = 0
            if builtin_name in LOW_RATIO_BUILTINS:
                assert isinstance(builtin, BuiltinInstanceDefWithLowRatio)
                builtins_params_dict[f"{builtin_name}_ratio_den"] = builtin.ratio_den

        return CairoLayoutParams(
            cpu_component_step=cairo_layout.cpu_component_step,
            rc_units=cairo_layout.rc_units,
            memory_units_per_step=cairo_layout.memory_units_per_step,
            log_diluted_units_per_step=cairo_layout.diluted_pool_instance_def.log_units_per_step,
            **builtins_params_dict,
        )

    def get_builtin_ratio(self, builtin_name: str) -> int:
        assert builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN)
        return getattr(self, f"{builtin_name}_ratio")

    def get_builtin_ratio_den(self, builtin_name: str) -> int:
        if builtin_name in LOW_RATIO_BUILTINS:
            return getattr(self, f"{builtin_name}_ratio_den")
        return 1

    def get_builtin_row_ratio(self, builtin_name: str) -> int:
        return safe_div(
            COMPONENT_HEIGHT * self.cpu_component_step * self.get_builtin_ratio(builtin_name),
            self.get_builtin_ratio_den(builtin_name),
        )

    def get_uses_builtin(self, builtin_name: str) -> int:
        assert builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN)
        return getattr(self, f"uses_{builtin_name}_builtin")

    def to_cairo_layout(self) -> CairoLayout:
        builtin_ratios: dict[str, int] = {}
        for builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN):
            builtin_ratios[builtin_name] = self.get_builtin_ratio(builtin_name)
            if builtin_name in LOW_RATIO_BUILTINS:
                builtin_ratios[builtin_name + "_den"] = self.get_builtin_ratio_den(builtin_name)

        return build_dynamic_layout(
            log_diluted_units_per_step=self.log_diluted_units_per_step,
            cpu_component_step=self.cpu_component_step,
            rc_units=self.rc_units,
            memory_units_per_step=self.memory_units_per_step,
            **builtin_ratios,
        )


def dynamic_params_dict_to_cairo_layout_params(
    dynamic_params_dict: Dict[str, int]
) -> CairoLayoutParams:
    """
    Creates a CairoLayoutParams object from a dynamic params dictionary.
    """
    builtins_params_dict: Dict[str, int] = {}
    for builtin_name, row_ratio_name in ROW_RATIO_NAMES.items():
        uses_builtin_str = f"uses_{builtin_name}_builtin"
        builtin_ratio_str = f"{builtin_name}_ratio"
        builtins_params_dict[uses_builtin_str] = dynamic_params_dict[uses_builtin_str]
        if builtin_name in LOW_RATIO_BUILTINS:
            builtins_params_dict[builtin_ratio_str + "_den"] = 1
        if builtins_params_dict[uses_builtin_str] == 1:
            # The builtin ratio can be calculated from the row_ratio as the fraction
            # `row_ratio / (COMPONENT_HEIGHT * cpu_component_step)`. After reduction, this fraction
            # must be in the form of either `ratio / 1` (in the general case) or `1 / ratio_den`
            # (only for low-ratio builtins).
            ratio_frac = Fraction(
                dynamic_params_dict[row_ratio_name],
                COMPONENT_HEIGHT * dynamic_params_dict["cpu_component_step"],
            )
            if ratio_frac.denominator != 1:
                assert ratio_frac.numerator == 1
                assert builtin_name in LOW_RATIO_BUILTINS
                builtins_params_dict[builtin_ratio_str] = 1
                builtins_params_dict[builtin_ratio_str + "_den"] = ratio_frac.denominator
            else:
                builtins_params_dict[builtin_ratio_str] = ratio_frac.numerator

        else:
            builtins_params_dict[builtin_ratio_str] = 0

    log_diluted_units_per_step = safe_log2(
        COMPONENT_HEIGHT * dynamic_params_dict["cpu_component_step"]
    ) - safe_log2(dynamic_params_dict["diluted_units_row_ratio"])
    return CairoLayoutParams(
        cpu_component_step=dynamic_params_dict["cpu_component_step"],
        rc_units=safe_div(
            COMPONENT_HEIGHT * dynamic_params_dict["cpu_component_step"],
            dynamic_params_dict["range_check_units_row_ratio"],
        ),
        memory_units_per_step=safe_div(
            COMPONENT_HEIGHT * dynamic_params_dict["cpu_component_step"],
            dynamic_params_dict["memory_units_row_ratio"],
        ),
        log_diluted_units_per_step=log_diluted_units_per_step,
        **builtins_params_dict,
    )
