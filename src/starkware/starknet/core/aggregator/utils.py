import dataclasses
import os
from typing import Dict, List

from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.math_utils import safe_div
from starkware.python.utils import get_source_dir_path
from starkware.starknet.core.aggregator.output_parser import OsOutput

AGGREGATOR_PROGRAM_HASH_RELATIVE_PATH = "src/starkware/starknet/core/aggregator/program_hash.json"
AGGREGATOR_PROGRAM_HASH_PATH = get_source_dir_path(
    AGGREGATOR_PROGRAM_HASH_RELATIVE_PATH,
    default_value=os.path.join(os.path.dirname(__file__), "program_hash.json"),
)


@dataclasses.dataclass
class StateEntryManager:
    """
    Represents the information required to build the StateEntry structs in the Cairo memory.
    """

    # A pointer to the end of the state entry instances, where a new instance can be written.
    state_entry_ptr: RelocatableValue
    # A pointer to the end of the dictionary of contract storage changes.
    storage_dict_ptr: RelocatableValue

    def add_state_entry(self, segments, class_hash: int, storage_changes: List[int], nonce: int):
        """
        Writes a new `StateEntry` instance to the memory.
        """
        self.storage_dict_ptr = segments.write_arg(ptr=self.storage_dict_ptr, arg=storage_changes)

        self.state_entry_ptr = segments.write_arg(
            ptr=self.state_entry_ptr,
            arg=[class_hash, self.storage_dict_ptr, nonce],
        )


class OsOutputToCairo:
    """
    Converts an `OsOutput` instance to the corresponding Cairo memory segments.
    """

    def __init__(self, segments: MemorySegmentManager):
        self._inner_storage: Dict[int, StateEntryManager] = {}
        self.storage_dict_ptr = segments.add()
        self.class_dict_ptr = segments.add()

    def process_os_output(
        self, segments: MemorySegmentManager, dst_ptr: RelocatableValue, os_output: OsOutput
    ):
        """
        Processes the given `OsOutput` and writes its data to the Cairo memory at `dst_ptr`.
        """
        # Handle L1<>L2 messages.
        messages_to_l1_start = segments.add_temp_segment()
        messages_to_l1_end = segments.write_arg(
            ptr=messages_to_l1_start, arg=os_output.messages_to_l1
        )
        messages_to_l2_start = segments.add_temp_segment()
        messages_to_l2_end = segments.write_arg(
            ptr=messages_to_l2_start, arg=os_output.messages_to_l2
        )

        state_diff = os_output.state_diff
        assert state_diff is not None, "Missing state diff information."

        # Handle contract state changes.
        storage_dict: List[MaybeRelocatable] = []
        for contract in state_diff.contracts:
            if contract.addr in self._inner_storage:
                state_entry = self._inner_storage[contract.addr]
            else:
                state_entry = self._inner_storage[contract.addr] = StateEntryManager(
                    state_entry_ptr=segments.add(),
                    storage_dict_ptr=segments.add(),
                )

                assert contract.prev_class_hash is not None, "Missing previous class hash."
                assert contract.prev_nonce is not None, "Missing previous nonce."
                # Write the initial `StateEntry` struct into memory.
                state_entry.add_state_entry(
                    segments=segments,
                    class_hash=contract.prev_class_hash,
                    storage_changes=[],
                    nonce=contract.prev_nonce,
                )

            storage_changes = []
            for key, (prev_value, new_value) in contract.storage_changes:
                storage_changes.append(key)
                assert prev_value is not None, "Missing previous value information."
                storage_changes.append(prev_value)
                storage_changes.append(new_value)

            assert contract.new_class_hash is not None, "Missing new class hash."
            assert contract.new_nonce is not None, "Missing new nonce."
            state_entry.add_state_entry(
                segments=segments,
                class_hash=contract.new_class_hash,
                storage_changes=storage_changes,
                nonce=contract.new_nonce,
            )

            storage_dict.append(contract.addr)
            storage_dict.append(state_entry.state_entry_ptr - 6)
            storage_dict.append(state_entry.state_entry_ptr - 3)

        storage_dict_ptr_start = self.storage_dict_ptr
        self.storage_dict_ptr = segments.write_arg(ptr=self.storage_dict_ptr, arg=storage_dict)

        # Handle compiled class changes.
        class_dict = []

        for class_hash, (prev_compiled_hash, new_compiled_hash) in state_diff.classes:
            assert prev_compiled_hash is not None, "Missing previous compiled class hash."
            class_dict.append(class_hash)
            class_dict.append(prev_compiled_hash)
            class_dict.append(new_compiled_hash)

        class_dict_ptr_start = self.class_dict_ptr
        self.class_dict_ptr = segments.write_arg(ptr=self.class_dict_ptr, arg=class_dict)

        # Write the `OsOutput` struct into memory.
        segments.write_arg(
            ptr=dst_ptr,
            arg=[
                # Header.
                [
                    [os_output.initial_root, os_output.final_root],
                    os_output.prev_block_number,
                    os_output.new_block_number,
                    os_output.prev_block_hash,
                    os_output.new_block_hash,
                    os_output.os_program_hash,
                    os_output.starknet_os_config_hash,
                    os_output.use_kzg_da,
                    os_output.full_output,
                ],
                # squashed_os_state_update.
                [
                    storage_dict_ptr_start,
                    safe_div(len(storage_dict), 3),
                    class_dict_ptr_start,
                    safe_div(len(class_dict), 3),
                ],
                # initial_carried_outputs.
                [messages_to_l1_start, messages_to_l2_start],
                # final_carried_outputs.
                [messages_to_l1_end, messages_to_l2_end],
            ],
        )
