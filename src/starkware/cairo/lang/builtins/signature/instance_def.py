import dataclasses

# Each signature consists of 2 cells (a public key and a message).
CELLS_PER_SIGNATURE = 2


@dataclasses.dataclass
class EcdsaInstanceDef:
    # Defines the ratio between the number of steps to the number of ECDSA instances.
    # For every ratio steps, we have one instance.
    ratio: int

    # Split to this many different components - for optimization.
    repetitions: int

    # Size of hash.
    height: int
    n_hash_bits: int
