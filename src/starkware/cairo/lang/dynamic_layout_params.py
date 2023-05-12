import dataclasses
from collections import defaultdict
from dataclasses import field
from typing import Dict

MAX_BUILTIN_RATIO = 2**20
DYNAMIC_LAYOUT_NAME = "dynamic"


@dataclasses.dataclass
class DynamicLayoutParams:
    # A map from a builtin name to its ratio.
    builtin_ratios: Dict[str, int] = field(default_factory=lambda: defaultdict(lambda: -1))

    # A map from a dynamic param name to its value.
    dynamic_params: Dict[str, int] = field(default_factory=lambda: defaultdict(lambda: -1))
