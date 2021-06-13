from collections import UserDict
from typing import Callable, Dict, List, Type

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # A dict of segment relocation rules mapping a segment index to a RelocatableValue.
        # See add_relocation_rule for more details.
        self.relocation_rules: Dict[int, RelocatableValue] = {}

    def _check_element(self, num: MaybeRelocatable, name: str, exc_type: Type[Exception]):
        """
        Checks that num is a valid Cairo value: positive int or relocatable.
        Currently, does not check that value < prime.
        """
        if isinstance(num, RelocatableValue):
            return
        if not isinstance(num, int):
            raise exc_type(f'{name} must be an int, not {type(num).__name__}.')
        if num < 0:
            raise exc_type(f'{name} must be nonnegative. Got {num}.')

    def add_relocation_rule(
            self, src_ptr: RelocatableValue, dest_ptr: RelocatableValue):
        """
        Adds a relocation rule that moves values from the 'src_ptr' segment to 'dest_ptr'.

        'src_ptr' must point to the start of a temporary segment (negative index with offset 0).
        Once a relocation rule is set the memory dict relocates value on the fly,
        allowing the VM to execute the assertion 'src_ptr' = 'dest_ptr'.

        Note that relocation rules are not applied to addresses during execution
        and consequently adding a relocation rule does not allow the VM to
        read the value at memory['dest_ptr'].
        """
        assert src_ptr.segment_index < 0, f'src_ptr.segment_index must be < 0, src_ptr={src_ptr}.'
        assert src_ptr.offset == 0, f'src_ptr.offset must be 0, src_ptr={src_ptr}.'
        segment_index = src_ptr.segment_index
        assert segment_index not in self.relocation_rules, \
            f'The segment with index {segment_index} already has a relocation rule.'

        self.relocation_rules[segment_index] = dest_ptr

    def relocate_value(self, value):
        """
        Relocates a value according to the relocation rules.

        The original value is returned if the relocation rules do not apply to value.
        """
        if not isinstance(value, RelocatableValue):
            return value

        segment_idx = value.segment_index
        if segment_idx >= 0:
            return value

        relocation = self.relocation_rules.get(segment_idx)
        if relocation is None:
            return value

        return relocation + value.offset

    def relocate_memory(self):
        """
        Relocates the memory according to the relocation rules and clears self.relocation_rules.
        """
        if len(self.relocation_rules) == 0:
            return

        self.data = {
            self.relocate_value(addr): self.relocate_value(value)
            for addr, value in self.items()
        }
        self.relocation_rules = {}

    def __getitem__(self, addr: MaybeRelocatable) -> MaybeRelocatable:
        self._check_element(addr, 'Memory address', KeyError)
        try:
            value = super().__getitem__(addr)
        except KeyError:
            raise UnknownMemoryError(addr) from None

        return self.relocate_value(value)

    def __setitem__(self, addr: MaybeRelocatable, value: MaybeRelocatable):
        self._check_element(addr, 'Memory address', KeyError)
        self._check_element(value, 'Memory value', ValueError)

        # Additionally, check that address doesn't have a negative offset.
        if isinstance(addr, RelocatableValue) and addr.offset < 0:
            raise ValueError(
                f'The offset of a relocatable value must be nonnegative. Found: {addr}.')

        current = self.data.setdefault(addr, value)
        self.verify_same_value(addr, current, value)

    def verify_same_value(self, addr, current, value):
        """
        Verifies that 'current' and 'value' are the same and throws an exception otherwise.
        This function can be overridden by subclasses.
        """
        if current != value:
            raise InconsistentMemoryError(addr, current, value)

    def set_without_checks(self, addr: MaybeRelocatable, value: MaybeRelocatable):
        """
        Same as __setitem__() except that no checks are performed on addr and value.
        This function should only be used in tests.
        """
        self.data[addr] = value

    def serialize(self, field_bytes):
        assert len(self.relocation_rules) == 0, \
            'Cannot serialize a MemoryDict with active segment relocation rules.'

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
