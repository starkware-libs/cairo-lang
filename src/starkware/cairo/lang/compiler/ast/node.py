from abc import ABC, abstractmethod
from typing import Optional, Sequence


class AstNode(ABC):
    @abstractmethod
    def get_children(self) -> Sequence[Optional['AstNode']]:
        """
        Returns a list of the node's children (notes are not included).
        """
