import dataclasses

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef

# Each signature consists of 2 cells (a public key and a message).
CELLS_PER_SIGNATURE = INPUT_CELLS_PER_SIGNATURE = 2


@dataclasses.dataclass
class EcdsaInstanceDef(BuiltinInstanceDef):
    # Split to this many different components - for optimization.
    repetitions: int

    # Size of hash.
    height: int
    n_hash_bits: int

    @property
    def memory_cells_per_instance(self) -> int:
        return CELLS_PER_SIGNATURE

    @property
    def range_check_units_per_builtin(self) -> int:
        return 0

    @property
    def invocation_height(self) -> int:
        return 2 * self.height

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return 0
