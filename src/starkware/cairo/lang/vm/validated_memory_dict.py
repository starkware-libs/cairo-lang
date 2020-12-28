from typing import Callable, Dict, List, Set, Tuple

from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue

ValidationRule = Callable[['MemoryDict', RelocatableValue], Set[RelocatableValue]]


class ValidatedMemoryDict:
    """
    A proxy to MemoryDict which validates memory values in specific segments upon writing to it.
    Validation is done according to the validation rules.
    """

    def __init__(self, memory):
        self.__memory: MemoryDict = memory
        # validation_rules contains a mapping from a segment index to a list of functions
        # (and a tuple of additional arguments) that may try to validate the value of memory cells
        # in the segment (sometimes based on other memory cells).
        self.__validation_rules: Dict[int, List[Tuple[ValidationRule, tuple]]] = {}
        # A list of addresses which were already validated.
        self.__validated_addresses: Set[RelocatableValue] = set()

    def __getitem__(self, addr: MaybeRelocatable) -> MaybeRelocatable:
        return self.__memory[addr]

    def __setitem__(self, addr: MaybeRelocatable, value: MaybeRelocatable):
        self.__memory[addr] = value
        if isinstance(addr, RelocatableValue) and addr not in self.__validated_addresses:
            for rule, args in self.__validation_rules.get(addr.segment_index, []):
                validated_addresses = rule(self.__memory, addr, *args)
                self.__validated_addresses |= validated_addresses

    def __getattr__(self, name: str):
        if name in ['__deepcopy__', '__getstate__', '__setstate__']:
            raise AttributeError(f'ValidatedMemoryDict has no attribute named {name}.')
        return getattr(self.__memory, name)

    def __iter__(self):
        return iter(self.__memory)

    def add_validation_rule(self, segment_index, rule: ValidationRule, *args):
        """
        Adds a validation rule on the given segment, which will be called upon writing to this
        segment (using setitem).
        'rule' is a callback function that gets the current memory, a memory address within the
        given segment and possibly some auxillary arguments, which are the given args.
        The rule output is assumed to be the set of memory addresses validated by it.
        """
        self.__validation_rules.setdefault(segment_index, []).append((rule, args))
