import dataclasses
from typing import Dict

from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.vm_consts import VmConstsReference


@dataclasses.dataclass
class DictTracker:
    """
    Tracks the python dict associated with a Cairo dict.
    """
    # Python dict.
    data: dict
    # Pointer to the first unused position in the dict segment.
    current_ptr: RelocatableValue


class DictManager:
    """
    Manages dictionaries in a Cairo program.
    Uses the segment index to associate the corresponding python dict with the Cairo dict.
    """

    def __init__(self):
        # Mapping from segment index to the corresponding DictTracker of the Cairo dict.
        self.trackers: Dict[int, DictTracker] = {}

    def new_dict(self, segments, initial_dict):
        """
        Creates a new Cairo dictionary. The values of initial_dict can be integers, tuples or
        lists. See MemorySegments.gen_arg().
        """
        base = segments.add()
        assert base.segment_index not in self.trackers
        self.trackers[base.segment_index] = DictTracker(
            data={
                key: segments.gen_arg(value) for key, value in initial_dict.items()},
            current_ptr=base,
        )
        return base

    def get_tracker(self, dict_ptr):
        """
        Gets a dict tracker given the dict_ptr.
        """
        if isinstance(dict_ptr, VmConstsReference):
            dict_ptr = dict_ptr.address_
        dict_tracker = self.trackers.get(dict_ptr.segment_index)
        if dict_tracker is None:
            raise ValueError(f'Dictionary pointer {dict_ptr} was not created using dict_new().')
        assert dict_tracker.current_ptr == dict_ptr, 'Wrong dict pointer supplied. ' \
            f'Got {dict_ptr}, expected {dict_tracker.current_ptr}.'
        return dict_tracker

    def get_dict(self, dict_ptr) -> dict:
        """
        Gets the python dict that corresponds to dict_ptr.
        """
        return self.get_tracker(dict_ptr).data
