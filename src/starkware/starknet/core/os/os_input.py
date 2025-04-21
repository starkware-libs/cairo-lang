import logging
from dataclasses import field
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, cast

import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.starknet.business_logic.execution.objects import TransactionExecutionInfo
from starkware.starknet.business_logic.fact_state.contract_class_objects import ContractClassLeaf
from starkware.starknet.business_logic.fact_state.contract_state_objects import (
    ContractState,
    FactFetchingContext,
)
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.business_logic.transaction.deprecated_objects import (
    DeprecatedInternalDeclare,
    InternalL1Handler,
)
from starkware.starknet.business_logic.transaction.internal_account_transaction import (
    InternalAccountTransaction,
)
from starkware.starknet.business_logic.transaction.internal_transaction_schema import (
    InternalTransactionSchema,
)
from starkware.starknet.business_logic.transaction.objects import InternalTransaction
from starkware.starknet.core.os.os_utils import (
    fetch_compiled_classes,
    fetch_deprecated_compiled_classes,
)
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_class.contract_class import (
    CompiledClass,
    DeprecatedCompiledClass,
)
from starkware.starknet.storage.starknet_storage import (
    CommitmentInfo,
    OsSingleStarknetStorageData,
    PatriciaTree,
)
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

logger = logging.getLogger(__name__)


@marshmallow_dataclass.dataclass(frozen=True)
class CategorizedClassHash(ValidatedMarshmallowDataclass):
    # Mapping from class hash to compiled class hash.
    compiled_class_hashes: Dict[int, int]
    # Set of deprecated class hashes.
    deprecated_class_hashes: Set[int]

    @classmethod
    async def create(
        cls,
        class_hashes: FrozenSet[int],
        ffc: FactFetchingContext,
        contract_class_tree: Optional[PatriciaTree],
    ) -> "CategorizedClassHash":
        """
        Returns a mapping from class hash to compiled class hash, for v1 classes,
        and the v0 class hashes in a separate set.
        """
        if contract_class_tree is None:
            # The state is old and does not contain a class commitment tree;
            # All class hashes are deprecated class hashes.
            return CategorizedClassHash(
                compiled_class_hashes={}, deprecated_class_hashes=cast(Set[int], class_hashes)
            )

        compiled_class_hash_mapping = await contract_class_tree.get_leaves(
            ffc=ffc,
            indices=class_hashes,
            fact_cls=ContractClassLeaf,
        )

        class_hash_to_compiled_class_hash = {
            class_hash: compiled_class_hash_leaf.compiled_class_hash
            for class_hash, compiled_class_hash_leaf in compiled_class_hash_mapping.items()
            if not compiled_class_hash_leaf.is_empty
        }

        # We assume that uncommitted classes (i.e., with compiled_class_hash==0) are·
        # the deprecated ones.
        deprecated_class_hashes = {
            class_hash
            for class_hash, compiled_class_hash_leaf in compiled_class_hash_mapping.items()
            if compiled_class_hash_leaf.is_empty
        }

        return CategorizedClassHash(
            compiled_class_hashes=class_hash_to_compiled_class_hash,
            deprecated_class_hashes=deprecated_class_hashes,
        )

    async def fetch_compiled_classes_with_deprecated(self, ffc: FactFetchingContext):
        compiled_classes = await fetch_compiled_classes(
            compiled_class_hashes=self.compiled_class_hashes.values(),
            fact_storage=ffc.storage,
        )
        deprecated_compiled_classes = await fetch_deprecated_compiled_classes(
            compiled_class_hashes=self.deprecated_class_hashes,
            fact_storage=ffc.storage,
        )
        logger.info(
            f"Number of compiled classes: {len(compiled_classes)}; total bytecode size: "
            + str(sum(len(compiled_class.bytecode) for compiled_class in compiled_classes.values()))
        )
        logger.info(
            f"Number of deprecated compiled classes: {len(deprecated_compiled_classes)}; "
            + f"total bytecode size: "
            + str(
                sum(
                    len(compiled_class.program.data)
                    for compiled_class in deprecated_compiled_classes.values()
                )
            ),
        )

        logger.info("Finished fetching contract classes.")

        return compiled_classes, deprecated_compiled_classes

    @classmethod
    def merge(
        cls, categorized_class_hashes: List["CategorizedClassHash"]
    ) -> "CategorizedClassHash":
        """
        Merge list of categorized class hashes into a single categorized class hash.
        """
        compiled_class_hashes = {}
        deprecated_class_hashes = set()
        for categorized_class_hash in categorized_class_hashes:
            compiled_class_hashes.update(categorized_class_hash.compiled_class_hashes)
            deprecated_class_hashes.update(categorized_class_hash.deprecated_class_hashes)
        return CategorizedClassHash(
            compiled_class_hashes=compiled_class_hashes,
            deprecated_class_hashes=deprecated_class_hashes,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class OsBlockInput(ValidatedMarshmallowDataclass):
    block_info: BlockInfo
    contract_state_commitment_info: CommitmentInfo
    contract_class_commitment_info: CommitmentInfo
    address_to_storage_commitment_info: Dict[int, CommitmentInfo]

    contracts: Dict[int, ContractState]
    class_hash_to_compiled_class_hash: Dict[int, int]
    general_config: StarknetGeneralConfig
    transactions: Sequence[InternalTransaction] = field(
        metadata=dict(marshmallow_field=mfields.List(mfields.Nested(InternalTransactionSchema)))
    )
    tx_execution_infos: List[TransactionExecutionInfo]
    storage_by_address: Dict[int, OsSingleStarknetStorageData]
    # A mapping from Cairo 1 declared class hashes to the hashes of the contract class components.
    declared_class_hash_to_component_hashes: Dict[int, List[int]]
    prev_block_hash: int
    new_block_hash: int
    # The block number and block hash of the (current_block_number - buffer) block, where
    # buffer=STORED_BLOCK_HASH_BUFFER.
    # It is the hash that is going to be written by this OS run.
    old_block_number_and_hash: Optional[tuple[int, int]]

    def __post_init__(self):
        super().__post_init__()
        for tx in self.transactions:
            if isinstance(tx, InternalAccountTransaction):
                assert tx.version >= 3, f"Invalid transaction version: {tx.version}."
                assert (
                    len(tx.resource_bounds) == 3
                ), f"Invalid resource bounds: {tx.resource_bounds}."
            elif isinstance(tx, DeprecatedInternalDeclare):
                assert tx.version == 0, f"Invalid Declare version: {tx.version}."
            else:
                assert isinstance(
                    tx, InternalL1Handler
                ), f"Invalid transaction type: {type(tx).__name__}."


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetOsInput(ValidatedMarshmallowDataclass):
    block_inputs: List[OsBlockInput]
    deprecated_compiled_classes: Dict[int, DeprecatedCompiledClass] = field(
        metadata=fields.new_class_hash_dict_keys_metadata(
            values_schema=DeprecatedCompiledClass.Schema
        )
    )
    compiled_classes: Dict[int, CompiledClass] = field(
        metadata=fields.new_class_hash_dict_keys_metadata(values_schema=CompiledClass.Schema)
    )

    def __post_init__(self):
        self.validate_block_inputs()
        return super().__post_init__()

    def validate_block_inputs(self):
        assert len(self.block_inputs) > 0, "OS input must have at least one block."

        block_numbers = [block_input.block_info.block_number for block_input in self.block_inputs]
        assert all(
            block_numbers[i] + 1 == block_numbers[i + 1] for i in range(len(block_numbers) - 1)
        ), "OS input must have consecutive block numbers."

        assert all(
            block_input.block_info.use_kzg_da == self.block_inputs[0].block_info.use_kzg_da
            for block_input in self.block_inputs
        ), "All blocks in OS inputs must have the same use_kzg_da."

    @classmethod
    async def from_block_inputs(
        cls,
        block_inputs: List[OsBlockInput],
        categorized_class_hash: CategorizedClassHash,
        ffc: FactFetchingContext,
    ) -> "StarknetOsInput":
        (
            compiled_classes,
            deprecated_compiled_classes,
        ) = await categorized_class_hash.fetch_compiled_classes_with_deprecated(ffc=ffc)
        return cls(
            block_inputs=block_inputs,
            deprecated_compiled_classes=deprecated_compiled_classes,
            compiled_classes=compiled_classes,
        )

    @property
    def use_kzg_da(self) -> bool:
        # Can't fail and well defined because of the validation in __post_init__.
        return self.block_inputs[0].block_info.use_kzg_da
