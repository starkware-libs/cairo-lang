import dataclasses
from dataclasses import field

from starkware.python.utils import from_bytes
from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactTree
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.starkware_utils.validated_fields import int_as_hex_metadata


@dataclasses.dataclass(frozen=True)
class BinaryFactTreeDiff(ValidatedDataclass):
    initial_root: int = field(metadata=int_as_hex_metadata(validated_field=None))
    final_root: int = field(metadata=int_as_hex_metadata(validated_field=None))
    height: int

    @classmethod
    def from_trees(
        cls, initial_tree: BinaryFactTree, final_tree: BinaryFactTree
    ) -> "BinaryFactTreeDiff":
        return cls(
            initial_root=from_bytes(initial_tree.root),
            final_root=from_bytes(final_tree.root),
            height=final_tree.height,
        )
