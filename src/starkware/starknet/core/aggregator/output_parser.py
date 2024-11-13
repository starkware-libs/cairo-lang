import dataclasses
import itertools
from typing import Dict, Iterator, List, Optional, Tuple

from starkware.starknet.core.os.data_availability.compression import compress, decompress
from starkware.starknet.definitions.constants import OsOutputConstant

N_UPDATES_BOUND = 2**64
N_UPDATES_SMALL_PACKING_BOUND = 2**8
NONCE_BOUND = 2**64
FLAG_BOUND = 2**1


@dataclasses.dataclass
class ContractChanges:
    """
    Represents the changes in a contract instance.
    """

    # The address of the contract.
    addr: int
    # The previous nonce of the contract (for account contracts, if full output).
    prev_nonce: Optional[int]
    # The new nonce of the contract (for account contracts, if changed or full output).
    new_nonce: Optional[int]
    # The previous class hash (if full output).
    prev_class_hash: Optional[int]
    # The new class hash (if changed or full output).
    new_class_hash: Optional[int]
    # A map from storage key to its prev value (optional) and new value.
    storage_changes: Dict[int, Tuple[Optional[int], int]]

    def encode(self, full_output: bool = False) -> List[int]:
        """
        Returns the OS encoding of the contract diff.
        """
        was_class_updated = self.prev_class_hash != self.new_class_hash
        header_packed_word = self.encode_header(
            n_updates=len(self.storage_changes),
            prev_nonce=self.prev_nonce,
            new_nonce=self.new_nonce,
            class_updated=was_class_updated,
            full_output=full_output,
        )
        res = [self.addr, header_packed_word]

        if full_output:
            assert self.prev_class_hash is not None, "Prev class_hash is missing with full_output."
            assert self.new_class_hash is not None, "New class_hash is missing with full_output."
            res += [self.prev_class_hash, self.new_class_hash]
        else:
            if was_class_updated:
                assert self.new_class_hash is not None
                res.append(self.new_class_hash)

        res += encode_key_value_pairs(self.storage_changes)
        return res

    @staticmethod
    def encode_header(
        n_updates: int,
        prev_nonce: Optional[int],
        new_nonce: Optional[int],
        class_updated: int,
        full_output: bool,
    ) -> int:
        """
        Returns the encoded contract header word.
        """
        if full_output:
            assert prev_nonce is not None, "Prev nonce is missing with full_output."
            assert new_nonce is not None, "New nonce is missing with full_output."
            packed_nonces = prev_nonce * NONCE_BOUND + new_nonce
        else:
            if new_nonce is None or prev_nonce == new_nonce:
                # The nonce was not changed.
                packed_nonces = 0
            else:
                packed_nonces = new_nonce

        is_n_updates_small = n_updates < N_UPDATES_SMALL_PACKING_BOUND
        n_updates_bound = N_UPDATES_SMALL_PACKING_BOUND if is_n_updates_small else N_UPDATES_BOUND

        header_packed_word = packed_nonces
        header_packed_word = header_packed_word * n_updates_bound + n_updates
        header_packed_word = header_packed_word * FLAG_BOUND + int(is_n_updates_small)
        header_packed_word = header_packed_word * FLAG_BOUND + int(class_updated)
        return header_packed_word


@dataclasses.dataclass(frozen=True)
class OsStateDiff:
    """
    Represents the state diff.
    """

    # Contracts that were changed.
    contracts: List[ContractChanges]
    # Classes that were declared. A map from class hash to previous (optional) and new
    # compiled class hash.
    classes: Dict[int, Tuple[Optional[int], int]]

    def encode(self, full_output: bool = False) -> List[int]:
        """
        Returns the OS encoding of the state diff.
        """
        state_diff = [
            len(self.contracts),
            *list(itertools.chain(*(contract.encode() for contract in self.contracts))),
            len(self.classes),
            *encode_key_value_pairs(self.classes),
        ]
        if not full_output:
            return compress(data=state_diff)

        return state_diff


def encode_key_value_pairs(d: Dict[int, Tuple[Optional[int], int]]) -> List[int]:
    """
    Encodes a dictionary of the following format: {key: (optional_prev_value, new_value)}.
    """
    res = []
    for key, (prev_value, new_value) in sorted(d.items()):
        res.append(key)
        if prev_value is not None:
            res.append(prev_value)
        res.append(new_value)

    return res


@dataclasses.dataclass
class OsOutput:
    """
    Represents the output of the OS.
    """

    # The root before.
    initial_root: int
    # The root after.
    final_root: int
    # The previous block number.
    prev_block_number: int
    # The new block number.
    new_block_number: int
    # The previous block hash.
    prev_block_hash: int
    # The new block hash.
    new_block_hash: int
    # The hash of the OS program, if the aggregator was used. Zero if the OS was used directly.
    os_program_hash: int
    # The hash of the OS config.
    starknet_os_config_hash: int
    # Indicates whether KZG data availability was used.
    use_kzg_da: int
    # Indicates whether previous state values are included in the state update information.
    full_output: int
    # Messages from L2 to L1.
    messages_to_l1: List[int]
    # Messages from L1 to L2.
    messages_to_l2: List[int]
    # The state diff.
    state_diff: Optional[OsStateDiff]


@dataclasses.dataclass
class TaskOutput:
    """
    Represents the output of the OS.
    """

    program_hash: int
    os_output: OsOutput


def parse_bootloader_output(output: List[int]) -> List[TaskOutput]:
    """
    Parses the output of the bootloader, assuming the tasks are instances of the Starknet OS.
    """
    output_iter = iter(output)

    n_tasks = next(output_iter)
    tasks = []
    for _ in range(n_tasks):
        next(output_iter)  # Output size.
        program_hash = next(output_iter)
        tasks.append(
            TaskOutput(
                program_hash=program_hash, os_output=parse_os_output(output_iter=output_iter)
            )
        )

    assert next(output_iter, None) is None, "Bootloader output wasn't fully consumed."

    return tasks


def parse_os_output(output_iter: Iterator[int]) -> OsOutput:
    """
    Parses the output of the Starknet OS.
    """
    initial_root = next(output_iter)
    final_root = next(output_iter)
    prev_block_number = next(output_iter)
    new_block_number = next(output_iter)
    prev_block_hash = next(output_iter)
    new_block_hash = next(output_iter)
    os_program_hash = next(output_iter)
    starknet_os_config_hash = next(output_iter)
    use_kzg_da = next(output_iter)
    full_output_int = next(output_iter)

    assert full_output_int in [0, 1], f"Invalid full_output flag: {full_output_int}"
    assert use_kzg_da in [0, 1], f"Invalid KZG flag: {use_kzg_da}"

    full_output = full_output_int != 0

    if use_kzg_da == 1:
        # Skip KZG data.
        kzg_segment = list(itertools.islice(output_iter, 2))
        n_blobs = kzg_segment[OsOutputConstant.KZG_N_BLOBS_OFFSET.value]
        # Skip 'n_blobs' commitments and evaluations.
        list(itertools.islice(output_iter, 2 * 2 * n_blobs))

    # Handle messages.
    messages_to_l1_segment_size = next(output_iter)
    messages_to_l1 = list(itertools.islice(output_iter, messages_to_l1_segment_size))
    messages_to_l2_segment_size = next(output_iter)
    messages_to_l2 = list(itertools.islice(output_iter, messages_to_l2_segment_size))

    state_diff = (
        parse_os_state_diff(output_iter=output_iter, full_output=full_output)
        if use_kzg_da == 0
        else None
    )

    return OsOutput(
        initial_root=initial_root,
        final_root=final_root,
        prev_block_number=prev_block_number,
        new_block_number=new_block_number,
        prev_block_hash=prev_block_hash,
        new_block_hash=new_block_hash,
        os_program_hash=os_program_hash,
        starknet_os_config_hash=starknet_os_config_hash,
        use_kzg_da=use_kzg_da,
        full_output=full_output_int,
        messages_to_l1=messages_to_l1,
        messages_to_l2=messages_to_l2,
        state_diff=state_diff,
    )


def parse_os_state_diff(output_iter: Iterator[int], full_output: bool) -> OsStateDiff:
    """
    Parses the state diff.
    """
    if not full_output:
        state_diff = decompress(compressed=output_iter)
        output_iter = itertools.chain(iter(state_diff), output_iter)

    # Contract changes.
    n_contracts = next(output_iter)
    contracts = []
    for _ in range(n_contracts):
        contracts.append(parse_contract_changes(output_iter=output_iter, full_output=full_output))

    # Class changes.
    n_classes = next(output_iter)
    classes = {}
    for _ in range(n_classes):
        class_hash = next(output_iter)
        prev_compiled_class_hash = next(output_iter) if full_output else None
        new_compiled_class_hash = next(output_iter)
        classes[class_hash] = (prev_compiled_class_hash, new_compiled_class_hash)

    return OsStateDiff(contracts=contracts, classes=classes)


def parse_contract_changes(output_iter: Iterator[int], full_output: bool) -> ContractChanges:
    """
    Parses contract changes.
    """
    addr = next(output_iter)
    nonce_n_changes_two_flags = next(output_iter)

    # Parse flags.
    nonce_n_changes_one_flag, class_updated = divmod(nonce_n_changes_two_flags, FLAG_BOUND)
    nonce_n_changes, is_n_updates_small = divmod(nonce_n_changes_one_flag, FLAG_BOUND)

    # Parse n_changes.
    n_updates_bound = N_UPDATES_SMALL_PACKING_BOUND if is_n_updates_small else N_UPDATES_BOUND
    nonce, n_changes = divmod(nonce_n_changes, n_updates_bound)

    # Parse nonces.
    prev_nonce: Optional[int]
    new_nonce: Optional[int]
    if full_output:
        prev_nonce, new_nonce = divmod(nonce, NONCE_BOUND)
    else:
        prev_nonce = None
        new_nonce = None if nonce == 0 else nonce

    if full_output:
        prev_class_hash = next(output_iter)
        new_class_hash = next(output_iter)
    elif class_updated != 0:
        prev_class_hash = None
        new_class_hash = next(output_iter)
    else:
        prev_class_hash, new_class_hash = None, None

    storage_changes = {}
    for _ in range(n_changes):
        key = next(output_iter)
        prev_value = next(output_iter) if full_output else None
        new_value = next(output_iter)
        storage_changes[key] = (prev_value, new_value)

    return ContractChanges(
        addr=addr,
        prev_nonce=prev_nonce,
        new_nonce=new_nonce,
        prev_class_hash=prev_class_hash,
        new_class_hash=new_class_hash,
        storage_changes=storage_changes,
    )
