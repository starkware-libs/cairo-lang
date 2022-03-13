from abc import ABC, abstractmethod
from typing import Optional, cast

from services.external_api.utils import join_routes


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
    def format_uri(cls, name: str, version: Optional[str] = None) -> str:
        """
        Concatenates version/cls.prefix with given URI.
        """
        prefix = cast(str, cls.prefix)  # Mypy sees the property as a callable.
        route_list = [s for s in [version, prefix, name] if s is not None and len(s) != 0]
        return join_routes(route_list=route_list)
