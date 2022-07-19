import enum
from enum import Enum


@enum.unique
class UniqueNameKind(Enum):
    Label = "lbl"
    Func = "func"
    Var = "var"


class UniqueNameProvider:
    """
    Provides new compilation-unique names.

    The only instance of this class should be maintained by ``PassManagerContext``.
    It can be used to obtain names for anonymous code elements like labels, variables and functions.
    """

    # Dollar is not a valid identifier character in Cairo, thus we can be sure that
    # the name won't collide with identifiers in the source code.
    PREFIX = "$"

    def __init__(self):
        self.counter: int = 0

    def next(self, kind: UniqueNameKind) -> str:
        """
        Returns a new compilation-unique name that is guaranteed to be impossible to declare
        by the source code.

        The ``kind`` enum is only used to denote the purpose of generated names.
        All unique names, no matter what kind, use one shared global counter.
        """
        counter = self.counter
        self.counter += 1
        return f"{self.PREFIX}{kind.value}{counter}"

    @classmethod
    def is_name_unique(cls, name: str) -> bool:
        """
        Returns ``True`` if the given label seems to have been generated.
        """
        return name.startswith(cls.PREFIX)
