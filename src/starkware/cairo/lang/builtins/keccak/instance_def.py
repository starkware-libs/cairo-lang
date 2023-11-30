import dataclasses
from typing import List

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef
from starkware.python.math_utils import safe_div

HEIGHT = 32768
KECCAK_BATCH_SIZE = 16


@dataclasses.dataclass
class KeccakInstanceDef(BuiltinInstanceDef):
    # Note that diluted_n_bits invocations fit into one component instance, hence for every
    # (diluted_n_bits * ratio) steps, we have one Keccak component instance.

    # The input and output are 1600 bits that are represented using a sequence of field elements in
    # the following pattern. For example [64] * 25 means 25 field elements each containing 64 bits.
    state_rep: List[int]

    # Should equal n_diluted_bits.
    instances_per_component: int

    @property
    def memory_cells_per_instance(self) -> int:
        return 2 * len(self.state_rep)

    @property
    def range_check_units_per_builtin(self) -> int:
        return 0

    @property
    def invocation_height(self) -> int:
        return HEIGHT

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        # The diluted cells are:
        # state - 25 rounds times 1600 elements.
        # parity - 24 rounds times 1600/5 elements times 3 auxiliaries.
        # after_theta_rho_pi - 24 rounds times 1600 elements.
        # theta_aux - 24 rounds times 1600 elements.
        # chi_iota_aux - 24 rounds times 1600 elements times 2 auxiliaries.
        # In total 25 * 1600 + 24 * 320 * 3 + 24 * 1600 + 24 * 1600 + 24 * 1600 * 2 = 216640.
        # But we actually allocate 4 virtual columns, of dimensions 64 * 1024, in which we embed the
        # real cells, and we don't free the unused ones.
        # So the real number is 4 * 64 * 1024 = 262144.
        return safe_div(2**18, diluted_n_bits)
