import dataclasses
from typing import ChainMap, Optional, Tuple

from starkware.cairo.lang.compiler.identifier_definition import IdentifierDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager, IdentifierScope
from starkware.cairo.lang.compiler.preprocessor.memento import Memento
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class ProxyIdentifierManager(IdentifierManager):
    """
    A lazy copy of an IdentifierManager.
    All changes to this proxy are not reflected on the parent IdentifierManager, unless
    apply() is called.
    """

    def __init__(self, parent: IdentifierManager):
        self.parent = parent
        self.root: ProxyIdentifierScope = ProxyIdentifierScope(manager=self, parent=parent.root)
        self.dict: ChainMap[ScopedName, IdentifierDefinition] = ChainMap({}, parent.dict)

    def apply(self):
        """
        Applies all accumulated changes to the parent identifier manager.
        """
        self.root._apply()
        self.parent.dict.update(self.dict.maps[0])


class ProxyIdentifierScope(IdentifierScope):
    def __init__(self, manager: IdentifierManager, parent: IdentifierScope):
        super().__init__(manager=manager, fullname=parent.fullname)
        self.parent = parent
        self.identifiers: ChainMap[str, IdentifierDefinition] = ChainMap({}, parent.identifiers)

    def get_single_scope(self, name: str) -> Optional["IdentifierScope"]:
        if name not in self.subscopes:
            parent_subscope = self.parent.get_single_scope(name)
            if parent_subscope is None:
                return None
            self.subscopes[name] = ProxyIdentifierScope(
                manager=self.manager, parent=parent_subscope
            )
        return self.subscopes[name]

    def add_subscope(self, first_name: str):
        self.subscopes[first_name] = ProxyIdentifierScope(
            manager=self.manager,
            parent=IdentifierScope(
                manager=self.parent.manager,
                fullname=self.fullname + first_name,
            ),
        )

    def _apply(self):
        self.parent.identifiers.update(self.identifiers.maps[0])
        for name, subscope in self.subscopes.items():
            assert isinstance(subscope, ProxyIdentifierScope)
            if name not in self.parent.subscopes:
                self.parent.subscopes[name] = subscope.parent
            subscope._apply()


@dataclasses.dataclass
class IdentifierManagerMemento(Memento[IdentifierManager]):
    original: IdentifierManager

    @classmethod
    def from_object(
        cls, value: IdentifierManager
    ) -> Tuple["IdentifierManagerMemento", IdentifierManager]:
        return cls(original=value), ProxyIdentifierManager(parent=value)

    def restore(self, value: IdentifierManager) -> IdentifierManager:
        return self.original

    def apply(self, value: IdentifierManager) -> IdentifierManager:
        assert isinstance(value, ProxyIdentifierManager)
        value.apply()
        return self.original
