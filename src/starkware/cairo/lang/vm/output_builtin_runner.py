import dataclasses
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

from starkware.cairo.lang.vm.builtin_runner import BuiltinRunner, BuiltinVerifier
from starkware.cairo.lang.vm.memory_segments import get_segment_used_size
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.utils import MemorySegmentAddresses


@dataclasses.dataclass
class PublicMemoryPage:
    start: int
    size: int


class OutputBuiltinRunner(BuiltinRunner):
    def __init__(self, included: bool):
        self.included = included
        # A map from page id to PublicMemoryPage. See add_page() for more details.
        self.pages: Dict[int, PublicMemoryPage] = {}
        # A map from attribute name to its value. Serialized as part of the additional data of the
        # builtin.
        self.attributes: Dict[str, dict] = {}

    def initialize_segments(self, runner):
        self.base = runner.segments.add()
        self.stop_ptr: Optional[RelocatableValue] = None

    def initial_stack(self) -> List[MaybeRelocatable]:
        assert self.base is not None, 'Uninitialized self.base.'
        return [self.base] if self.included else []

    def final_stack(self, runner, pointer):
        if self.included:
            self.stop_ptr = runner.vm_memory[pointer - 1]
            used = get_segment_used_size(self.base.segment_index, runner.vm_memory)
            assert self.stop_ptr == self.base + used, \
                'Invalid stop pointer for output. ' + \
                f'Expected: {self.base + used}, found: {self.stop_ptr}'
            return pointer - 1
        else:
            self.stop_ptr = self.base
            return pointer

    def get_used_cells(self, runner):
        size = get_segment_used_size(self.base.segment_index, runner.vm_memory)
        return size

    def get_used_instances(self, runner):
        # Output builtin has one cell per instance.
        return self.get_used_cells(runner)

    def get_allocated_memory_units(self, runner):
        # The output builtin uses only public memory units.
        return 0

    def get_used_cells_and_allocated_size(self, runner):
        size = self.get_used_cells(runner)
        return size, size

    def finalize_segments(self, runner):
        _, size = self.get_used_cells_and_allocated_size(runner)

        # A map from an offset to its page id.
        offset_to_page = {}
        for page_id, page in self.pages.items():
            assert page.start + page.size <= size, f'Page {page_id} is out of bounds.'
            for i in range(page.start, page.start + page.size):
                assert offset_to_page.setdefault(i, page_id) == page_id, \
                    f'Offset {i} was already assigned a page.'

        public_memory: List[Tuple[int, int]] = []
        for i in range(size):
            public_memory.append((i, offset_to_page.get(i, 0)))

        runner.segments.finalize(
            self.base.segment_index, size=size, public_memory=public_memory)

    def get_memory_segment_addresses(self, runner):
        return {'output': MemorySegmentAddresses(
            begin_addr=self.base,
            stop_ptr=self.stop_ptr,
        )}

    def add_page(self, page_id: int, page_start: MaybeRelocatable, page_size: int):
        """
        Marks page_size addresses, starting from address page_start (which must be in the output
        segment), as a page with the given page id.
        All public memory cells which were not assigned a page, will be in page 0.
        This function should be used in Cairo hints.
        """
        assert page_id not in self.pages, f'Page {page_id} was already assigned.'
        assert isinstance(page_start, RelocatableValue) and \
            page_start.segment_index == self.base.segment_index, \
            'page_start must be in the output segment.'
        start = page_start - self.base
        self.pages[page_id] = PublicMemoryPage(start=start, size=page_size)

    def add_attribute(self, attribute_name: str, attribute_value: dict):
        """
        Adds an attribute that will be added to the additional data of the builtin.
        attribute_value must be JSON-serializable.
        This function should be used in Cairo hints.
        """
        self.attributes[attribute_name] = attribute_value

    def get_additional_data(self):
        return {
            'pages': {
                str(page_id): [page_info.start, page_info.size]
                for page_id, page_info in sorted(self.pages.items())},
            'attributes': self.attributes,
        }

    def extend_additional_data(self, data, relocate_callback, data_is_trusted=True):
        assert isinstance(data, dict) and sorted(data.keys()) == ['attributes', 'pages'], \
            'Invalid output builtin data.'

        # Process the 'pages' field.
        assert isinstance(data['pages'], dict), 'Invalid output builtin pages field.'
        for page_id_str, values in data['pages'].items():
            assert isinstance(page_id_str, str) and \
                isinstance(values, list) and \
                len(values) == 2 and \
                all(isinstance(x, int) and 0 < x < 2**30 for x in values), \
                'Invalid output builtin pages field.'
            self.pages[int(page_id_str)] = PublicMemoryPage(start=values[0], size=values[1])

        # Process the 'attributes' field.
        assert isinstance(data['attributes'], dict), 'Invalid output builtin attributes field.'
        self.attributes.update(data['attributes'])

    def run_security_checks(self, runner):
        return

    def set_state(self, state):
        """
        Sets the state of the output builtin. This can be used before calling another program
        which manages its own memory pages and attributes.

        Usage example:
          old_state = output_builtin_runner.get_state()
          output_builtin_runner.clear_state()

          # Call inner program.

          output_builtin_runner.set_state(old_state)
        """
        self.base = state.base
        self.pages = state.pages
        self.attributes = state.attributes

    def new_state(self, base):
        """
        Clears the state of the output builtin and sets self.base to the given value.
        See set_state().
        """
        self.base = base
        self.pages = {}
        self.attributes = {}

    def get_state(self):
        """
        Returns the state of the output builtin. See set_state().
        """
        return SimpleNamespace(base=self.base, pages=self.pages, attributes=self.attributes)


class OutputBuiltinVerifier(BuiltinVerifier):
    def __init__(self, included: bool):
        self.included = included

    def expected_stack(self, public_input):
        if not self.included:
            return [], []

        addresses = public_input.memory_segments['output']
        assert 0 <= addresses.begin_addr <= addresses.stop_ptr < 2**64
        return [addresses.begin_addr], [addresses.stop_ptr]
