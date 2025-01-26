import dataclasses
import itertools
from typing import Iterator, List, Optional, Tuple

from starkware.python.utils import as_non_optional
from starkware.starknet.core.os.data_availability.compression import compress, decompress
from starkware.starknet.definitions.constants import OsOutputConstant

N_UPDATES_BOUND = 2**64
N_UPDATES_SMALL_PACKING_BOUND = 2**8
NONCE_BOUND = 2**64
FLAG_BOUND = 2**1

# Key, (prev_value, value).
DictEntry = Tuple[int, Tuple[Optional[int], int]]


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
    storage_changes: List[DictEntry]

    def encode(self, full_output: bool = False) -> List[int]:
        """
        Returns the OS encoding of the contract diff.
        """
        if full_output:
            full_header = [
                self.addr,
                as_non_optional(self.prev_nonce),
                as_non_optional(self.new_nonce),
                as_non_optional(self.prev_class_hash),
                as_non_optional(self.new_class_hash),
                len(self.storage_changes),
            ]
            return full_header + encode_key_value_pairs(
                self.storage_changes, full_output=full_output
            )

        # Encode packed output.
        was_class_updated = self.prev_class_hash != self.new_class_hash
        header_packed_word = self.encode_packed_header(
            n_updates=len(self.storage_changes),
            prev_nonce=self.prev_nonce,
            new_nonce=self.new_nonce,
            class_updated=was_class_updated,
        )
        res = [self.addr, header_packed_word]

        if was_class_updated:
            assert self.new_class_hash is not None
            res.append(self.new_class_hash)

        res += encode_key_value_pairs(self.storage_changes, full_output=full_output)
        return res

    @staticmethod
    def encode_packed_header(
        n_updates: int,
        prev_nonce: Optional[int],
        new_nonce: Optional[int],
        class_updated: int,
    ) -> int:
        """
        Returns the encoded contract header word, where `full_output` is off.
        """
        if new_nonce is None or prev_nonce == new_nonce:
            # The nonce was not changed.
            header_packed_word = 0
        else:
            header_packed_word = new_nonce

        is_n_updates_small = n_updates < N_UPDATES_SMALL_PACKING_BOUND
        n_updates_bound = N_UPDATES_SMALL_PACKING_BOUND if is_n_updates_small else N_UPDATES_BOUND

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
    classes: List[DictEntry]

    def encode(self, full_output: bool = False) -> List[int]:
        """
        Returns the OS encoding of the state diff.
        """
        state_diff = [
            len(self.contracts),
            *list(itertools.chain(*(contract.encode() for contract in self.contracts))),
            len(self.classes),
            *encode_key_value_pairs(self.classes, full_output=full_output),
        ]
        if not full_output:
            return compress(data=state_diff)

        return state_diff


def encode_key_value_pairs(items: List[DictEntry], full_output: bool) -> List[int]:
    """
    Encodes a list of tuples of the following format: (key, (optional_prev_value, new_value)).
    """
    res = []
    for key, (prev_value, new_value) in items:
        res.append(key)
        if full_output:
            assert prev_value is not None, "prev_value is missing with full_output."
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
    classes = []
    for _ in range(n_classes):
        class_hash = next(output_iter)
        prev_compiled_class_hash = next(output_iter) if full_output else None
        new_compiled_class_hash = next(output_iter)
        classes.append((class_hash, (prev_compiled_class_hash, new_compiled_class_hash)))

    return OsStateDiff(contracts=contracts, classes=classes)


def parse_contract_changes(output_iter: Iterator[int], full_output: bool) -> ContractChanges:
    """
    Parses contract changes.
    """
    if full_output:
        return ContractChanges(
            addr=next(output_iter),
            prev_nonce=next(output_iter),
            new_nonce=next(output_iter),
            prev_class_hash=next(output_iter),
            new_class_hash=next(output_iter),
            storage_changes=parse_storage_changes(
                n_changes=next(output_iter), output_iter=output_iter, full_output=full_output
            ),
        )

    addr = next(output_iter)
    # Parse packed info.
    nonce_n_changes_two_flags = next(output_iter)

    # Parse flags.
    nonce_n_changes_one_flag, class_updated = divmod(nonce_n_changes_two_flags, FLAG_BOUND)
    nonce_n_changes, is_n_updates_small = divmod(nonce_n_changes_one_flag, FLAG_BOUND)

    # Parse n_changes.
    n_updates_bound = N_UPDATES_SMALL_PACKING_BOUND if is_n_updates_small else N_UPDATES_BOUND
    nonce, n_changes = divmod(nonce_n_changes, n_updates_bound)

    # Parse nonce.
    new_nonce = None if nonce == 0 else nonce

    new_class_hash = next(output_iter) if class_updated != 0 else None
    return ContractChanges(
        addr=addr,
        prev_nonce=None,
        new_nonce=new_nonce,
        prev_class_hash=None,
        new_class_hash=new_class_hash,
        storage_changes=parse_storage_changes(
            n_changes=n_changes, output_iter=output_iter, full_output=full_output
        ),
    )


def parse_storage_changes(
    n_changes: int, output_iter: Iterator[int], full_output: bool
) -> List[DictEntry]:
    storage_changes = []
    for _ in range(n_changes):
        key = next(output_iter)
        prev_value = next(output_iter) if full_output else None
        new_value = next(output_iter)
        storage_changes.append((key, (prev_value, new_value)))
    return storage_changes
