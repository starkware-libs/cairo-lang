from collections import UserDict
from typing import Callable, List

from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue

ADDR_SIZE_IN_BYTES = 8


class UnknownMemoryError(KeyError):
    def __init__(self, addr):
        self.addr = addr
        super().__init__(f'Unknown value for memory cell at address {addr}.')

    __str__: Callable[[BaseException], str] = Exception.__str__


class InconsistentMemoryError(Exception):
    def __init__(self, addr, old_value, new_value):
        self.addr = addr
        self.old_value = old_value
        self.new_value = new_value
        super().__init__(
            f'Inconsistent memory assignment at address {addr}. {old_value} != {new_value}.')


class MemoryDict(UserDict):
    """
    Dictionary used for VM memory. Adds the following checks:
    * Checks that all memory addresses are valid.
    * getitem: Checks that the memory address is initialized.
    * setitem: Checks that memory value is not changed.
    """

    def _check_element(self, num: MaybeRelocatable, name: str):
        """
        Checks that num is a valid Cairo value: positive int or relocatable.
        Currently, does not check that value < prime.
        """
        if isinstance(num, RelocatableValue):
            return
        if not isinstance(num, int):
            raise ValueError(f'{name} must be an int, not {type(num).__name__}')
        if num < 0:
            raise ValueError(f'{name} must be positive. Got {num}')

    def __getitem__(self, addr: MaybeRelocatable) -> MaybeRelocatable:
        self._check_element(addr, 'Memory address')
        try:
            return super().__getitem__(addr)
        except KeyError:
            raise UnknownMemoryError(addr) from None

    def __setitem__(self, addr: MaybeRelocatable, value: MaybeRelocatable):
        self._check_element(addr, 'Memory address')
        self._check_element(value, 'Memory value')

        current = self.data.setdefault(addr, value)
        self.verify_same_value(addr, current, value)

    def verify_same_value(self, addr, current, value):
        """
        Verifies that 'current' and 'value' are the same and throws an exception otherwise.
        This function can be overridden by subclasses.
        """
        if current != value:
            raise InconsistentMemoryError(addr, current, value)

    def serialize(self, field_bytes):
        return b''.join(
            RelocatableValue.to_bytes(addr, ADDR_SIZE_IN_BYTES, 'little') +
            RelocatableValue.to_bytes(value, field_bytes, 'little')
            for addr, value in self.items())

    def get_range(self, addr, size) -> List[MaybeRelocatable]:
        return [self[addr + i] for i in range(size)]

    @classmethod
    def deserialize(cls, data, field_bytes):
        pair_size = ADDR_SIZE_IN_BYTES + field_bytes
        assert len(data) % (pair_size) == 0,\
            f'Data must consist of pairs of address (8 bytes) and value ({field_bytes} bytes).'
        pair_stream = (
            data[pair_size * i: pair_size * (i + 1)]
            for i in range(len(data) // pair_size))
        return cls(
            (
                RelocatableValue.from_bytes(pair[:ADDR_SIZE_IN_BYTES], 'little'),
                RelocatableValue.from_bytes(pair[ADDR_SIZE_IN_BYTES:], 'little')
            )
            for pair in pair_stream)
