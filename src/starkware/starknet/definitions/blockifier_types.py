# Modules should not be named `types`, as this may cause errors:
# https://stackoverflow.com/questions/43453414 .
from typing import Dict, Tuple

# Blockifier typedefs:

# Class hash to raw class. Where raw class is a JSON dictionary representing the class.
# We use a plain JSON instead of a Python object to save loading time.
RawDeprecatedDeclaredClassMapping = Dict[int, str]
# Class hash to (compiled class hash, raw class).
RawDeclaredClassMapping = Dict[int, Tuple[int, str]]
