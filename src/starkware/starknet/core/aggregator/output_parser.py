import dataclasses
import itertools
from typing import Dict, Iterator, List, Optional, Tuple

from starkware.starknet.definitions.constants import OsOutputConstant


@dataclasses.dataclass
class ContractChanges:
    """
    Represents the changes in a contract instance.
    """

    # The address of the contract.
    addr: int
    # The previous nonce of the contract (for account contracts, optional).
    prev_nonce: Optional[int]
    # The new nonce of the contract (for account contracts).
    new_nonce: int
    # The previous class hash (if changed).
    prev_class_hash: Optional[int]
    # The new class hash (if changed).
    new_class_hash: Optional[int]
    # A map from storage key to its prev value (optional) and new value.
    storage_changes: Dict[int, Tuple[Optional[int], int]]


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
    # The list of contracts that were changed.
    contracts: Optional[List[ContractChanges]]
    # The list of classes that were declared. A map from class hash to previous (optional) and new
    # compiled class hash.
    classes: Optional[Dict[int, Tuple[Optional[int], int]]]


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

    contracts: Optional[List[ContractChanges]]
    if use_kzg_da == 0:
        # Contract changes.
        n_contracts = next(output_iter)
        contracts = []
        for _ in range(n_contracts):
            contracts.append(
                parse_contract_changes(output_iter=output_iter, full_output=full_output)
            )

        # Class changes.
        n_classes = next(output_iter)
        classes = {}
        for _ in range(n_classes):
            class_hash = next(output_iter)
            prev_compiled_class_hash = next(output_iter) if full_output else None
            new_compiled_class_hash = next(output_iter)
            classes[class_hash] = (prev_compiled_class_hash, new_compiled_class_hash)
    else:
        contracts = classes = None

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
        contracts=contracts,
        classes=classes,
    )


def parse_contract_changes(output_iter: Iterator[int], full_output: bool) -> ContractChanges:
    """
    Parses contract changes.
    """
    addr = next(output_iter)
    class_nonce_n_changes = next(output_iter)
    class_nonce, n_changes = divmod(class_nonce_n_changes, 2**64)
    if full_output:
        class_nonce, prev_nonce = divmod(class_nonce, 2**64)
    else:
        prev_nonce = None
    class_updated, new_nonce = divmod(class_nonce, 2**64)
    assert class_updated in [0, 1], f"Invalid contract header: {class_nonce_n_changes}"

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
