import dataclasses

from starkware.python.utils import from_bytes, to_bytes
from starkware.storage.storage import Fact, HashFunctionType


@dataclasses.dataclass(frozen=True)
class LeafFact(Fact):
    value: int

    @classmethod
    def prefix(cls) -> bytes:
        return b"leaf"

    def serialize(self) -> bytes:
        return to_bytes(self.value)

    def _hash(self, hash_func: HashFunctionType) -> bytes:
        return self.serialize()

    @classmethod
    def deserialize(cls, data: bytes) -> "LeafFact":
        return cls(from_bytes(data))

    @classmethod
    def empty(cls) -> "LeafFact":
        return cls(value=0)
