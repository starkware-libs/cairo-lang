import dataclasses
from typing import Dict, Optional

from starkware.cairo.lang.builtins.all_builtins import OUTPUT_BUILTIN, SUPPORTED_DYNAMIC_BUILTINS
from starkware.cairo.lang.instances import COMPONENT_HEIGHT, CairoLayout, build_dynamic_layout
from starkware.python.math_utils import safe_div

MIN_BUILTIN_RATIO = 1
MAX_CPU_COMPONENT_STEP = 2**6
MAX_N_MEMORY_HOLES_PER_STEP = 2**10
MIN_KECCAK_RATIO = 2**6
MIN_MEMORY_UNITS_PER_STEP = 4
NUM_COLUMNS_FIRST_BOUND = 2**16
NUM_COLUMNS_SECOND_BOUND = 2**16


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
            ratio = cairo_layout.builtins[builtin_name].ratio
            assert ratio is not None
            if cairo_layout.builtins[builtin_name].is_used():
                builtins_params_dict[f"uses_{builtin_name}_builtin"] = 1
                builtins_params_dict[f"{builtin_name}_ratio"] = ratio
            else:
                builtins_params_dict[f"uses_{builtin_name}_builtin"] = 0
                builtins_params_dict[f"{builtin_name}_ratio"] = 0

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

    def get_builtin_row_ratio(self, builtin_name: str) -> int:
        return COMPONENT_HEIGHT * self.cpu_component_step * self.get_builtin_ratio(builtin_name)

    def get_uses_builtin(self, builtin_name: str) -> int:
        assert builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN)
        return getattr(self, f"uses_{builtin_name}_builtin")

    def to_cairo_layout(self) -> CairoLayout:
        builtin_ratios: dict[str, int] = {}
        for builtin_name in SUPPORTED_DYNAMIC_BUILTINS.except_for(OUTPUT_BUILTIN):
            builtin_ratios[builtin_name] = self.get_builtin_ratio(builtin_name)

        return build_dynamic_layout(
            log_diluted_units_per_step=self.log_diluted_units_per_step,
            cpu_component_step=self.cpu_component_step,
            rc_units=self.rc_units,
            memory_units_per_step=self.memory_units_per_step,
            **builtin_ratios,
        )
