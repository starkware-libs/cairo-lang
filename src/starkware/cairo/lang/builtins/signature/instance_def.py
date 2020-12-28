import dataclasses


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
