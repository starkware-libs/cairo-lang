from abc import ABC, abstractmethod
from typing import Iterator, Optional, Sequence


class AstNode(ABC):
    @abstractmethod
    def get_children(self) -> Sequence[Optional["AstNode"]]:
        """
        Returns a list of the node's children (notes are not included).
        """

    def get_subtree(self) -> Iterator["AstNode"]:
        """
        Returns an iterator of all non-None nodes in the subtree rooted at this node, preorder
        (visit each node before its children).
        """
        yield self
        for child in filter(None, self.get_children()):
            yield from child.get_subtree()
