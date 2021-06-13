from abc import ABC, abstractmethod
from typing import cast


class HasUriPrefix(ABC):
    """
    A base class of HTTP Gateway services.
    """
    @property
    @classmethod
    @abstractmethod
    def prefix(cls) -> str:
        """
        Returns the prefix of the gateway URIs.
        Subclasses should define it as a class variable.
        """

    @classmethod
    def format_uri(cls, name: str) -> str:
        """
        Concatenates cls.prefix with given URI.
        """
        prefix = cast(str, cls.prefix)  # Mypy sees the property as a callable.
        return name if len(prefix) == 0 else f'{cls.prefix}{name}'
