import dataclasses
from typing import Optional


# Should only include versioned constants which are both overridable AND have a need for an
# override.
@dataclasses.dataclass
class OverridableVersionedConstants:
    max_calldata_length: Optional[int] = None
    invoke_tx_max_n_steps: Optional[int] = None
    validate_max_n_steps: Optional[int] = None
