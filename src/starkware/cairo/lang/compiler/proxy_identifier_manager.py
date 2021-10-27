from typing import ChainMap, Dict, Optional

from starkware.cairo.lang.compiler.identifier_definition import IdentifierDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager, IdentifierScope


class ProxyIdentifierManager(IdentifierManager):
    """
    A lazy copy of an IdentifierManager.
    All changes to this proxy are not reflected on the parent IdentifierManager, unless
    apply() is called.
    """

    def __init__(self, parent: IdentifierManager):
        self.parent = parent
        self.root = ProxyIdentifierScope(manager=self, parent=parent.root)
        self.dict: ChainMap[str, IdentifierDefinition] = ChainMap({}, parent.dict)

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
        self.subscopes: Dict[str, IdentifierScope] = {}
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
            if name not in self.parent.subscopes:
                self.parent.subscopes[name] = subscope.parent
            subscope._apply()
