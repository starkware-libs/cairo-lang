import dataclasses


@dataclasses.dataclass
class CheckpointsInstanceDef:
    # Defines the ratio between the number of steps to the number of samples.
    # For every sample_ratio steps, we have one sample.
    sample_ratio: int
