import dataclasses
import functools
from typing import Callable, List

from starkware.cairo.lang.vm.crypto import pedersen_hash


def compute_hash_on_elements(data, hash_func=pedersen_hash):
    """
    Computes a hash chain over the data, in the following order:
        h(h(h(h(0, data[0]), data[1]), ...), data[n-1]), n).

    The hash is initialized with 0 and ends with the data length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    return functools.reduce(lambda x, y: hash_func(x, y), [*data, len(data)], 0)


def compute_hash_on_elements_without_length(data, hash_func=pedersen_hash):
    """
    Similar to `compute_hash_on_elements` but without appending the length.
    May be used for hashing a prefix of a hash chain.
    """
    return functools.reduce(lambda x, y: hash_func(x, y), data, 0)


@dataclasses.dataclass
class HashState:
    """
    Class to mimic behavior of the Cairo0 `HashState` struct.
    """

    current_hash: int
    n_words: int
    hash_func: Callable[[int, int], int]
    finalized: bool

    @classmethod
    def init(cls, hash_func: Callable[[int, int], int] = pedersen_hash) -> "HashState":
        return cls(current_hash=0, n_words=0, hash_func=hash_func, finalized=False)

    def update_single(self, value: int):
        assert not self.finalized, "Cannot update a finalized HashState."
        self.current_hash = self.hash_func(self.current_hash, value)
        self.n_words += 1

    def update_with_hashchain(self, values: List[int]):
        assert not self.finalized, "Cannot update a finalized HashState."
        n = len(values)
        data_hash = 0
        # If the data is empty, we update the hash with h(0, 0).
        for x in values:
            data_hash = self.hash_func(data_hash, x)
        self.update_single(value=self.hash_func(data_hash, n))

    def finalize(self) -> int:
        assert not self.finalized, "Cannot finalize twice."
        self.finalized = True
        return self.hash_func(self.current_hash, self.n_words)
