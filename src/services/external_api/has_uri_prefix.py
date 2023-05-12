from abc import ABC, abstractmethod
from typing import ClassVar, Optional, cast

from services.external_api.utils import join_routes


class HasUriPrefix(ABC):
    """
    A base class of HTTP Gateway services.
    """

    _version: ClassVar[str] = ""

    @property
    @classmethod
    @abstractmethod
    def prefix(cls) -> str:
        """
        Returns the prefix of the gateway URIs.
        Subclasses should define it as a class variable.
        """

    @classmethod
    def format_uri(cls, name: str, version: Optional[str] = None) -> str:
        """
        Concatenates version/cls.prefix with given URI.
        If version is not specified, cls._version is used.
        """
        version = version if version is not None else cls._version
        prefix = cast(str, cls.prefix)  # Mypy sees the property as a callable.
        route_list = [s for s in [prefix, version, name] if s is not None and len(s) != 0]
        return join_routes(route_list=route_list)
