import dataclasses
from typing import Dict, List, Optional, Set, Union

from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition, FutureIdentifierDefinition, IdentifierDefinition)
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class IdentifierError(Exception):
    pass


class MissingIdentifierError(IdentifierError):
    def __init__(self, fullname: ScopedName):
        self.fullname = fullname
        super().__init__(f"Unknown identifier '{fullname}'.")


class NotAScopeError(IdentifierError):
    """
    The requested identifier is not a scope.
    """

    def __init__(
            self, fullname: ScopedName, definition: IdentifierDefinition, non_parsed: ScopedName):
        self.fullname = fullname
        self.definition = definition
        self.non_parsed = non_parsed
        super().__init__(f"Identifier '{fullname}' is {definition.TYPE}, expected a scope.")


@dataclasses.dataclass
class IdentifierSearchResult:
    # The definition of the searched identifier.
    identifier_definition: IdentifierDefinition
    # The canonical name of the identifier.
    canonical_name: ScopedName
    # The suffix of the name which was not parsed.
    # For example, if one searches for 'x.y.z.w' and 'x.y' is a reference, then non_parsed
    # will contain 'z.w'.
    non_parsed: ScopedName

    def assert_fully_parsed(self):
        """
        Makes sure all name items were resolved (non_parsed is empty).
        Raises an IdentifierError otherwise.
        """
        if len(self.non_parsed) == 0:
            return
        raise IdentifierError(
            f"Unexpected '.' after '{self.canonical_name}' which is "
            f'{self.identifier_definition.TYPE}.')

    def get_canonical_name(self) -> ScopedName:
        """
        Returns the canonical name of the identifier and verifies it is fully resolved.
        """
        self.assert_fully_parsed()
        return self.canonical_name


class IdentifierManager:
    """
    Manages the list of identifiers and their definitions.
    """

    def __init__(self):
        self.root = IdentifierScope(self, ScopedName())
        self.dict = {}

    def add_identifier(self, name: ScopedName, definition: IdentifierDefinition):
        """
        Adds an identifier with the given name and definition.
        Allows overriding an existing definition.
        """
        self.root.add_identifier(name, definition)

    @classmethod
    def from_dict(
            cls, identifier_dict: Dict[ScopedName, IdentifierDefinition]) -> 'IdentifierManager':
        identifier_manager = cls()
        for name, identifier_definition in identifier_dict.items():
            identifier_manager.add_identifier(name, identifier_definition)
        return identifier_manager

    def as_dict(self):
        return self.dict

    def __eq__(self, other):
        if not isinstance(other, IdentifierManager):
            return False
        return self.as_dict() == other.as_dict()

    def get(self, name: ScopedName) -> IdentifierSearchResult:
        """
        Finds the identifier with the given name. Includes alias resolution and a possibly
        non-parsed part.
        For example, if name='x.y.z', 'x' is an alias to 'a.b', and 'a.b.y' is a
        Reference definition, the function will return that reference with non_parsed='z'.
        """
        current_identifier = name

        # Use a set of visited identifiers to detect cycles.
        visited_identifiers = [current_identifier]

        result = self.root.get(current_identifier)

        # Resolve aliases.
        while isinstance(result.identifier_definition, AliasDefinition):
            current_identifier = result.identifier_definition.destination + result.non_parsed

            # Detect cycles.
            if current_identifier in visited_identifiers:
                cycle_str = ' -> '.join(map(str, visited_identifiers + [current_identifier]))
                raise IdentifierError(f'Cyclic aliasing detected: {cycle_str}')
            visited_identifiers.append(current_identifier)

            try:
                result = self.root.get(current_identifier)
            except MissingIdentifierError as exc:
                resolution_str = ' -> '.join(map(str, visited_identifiers))
                raise IdentifierError(f'Alias resolution failed: {resolution_str}. {exc}')

        return result

    def get_by_full_name(self, name: ScopedName) -> Optional[IdentifierDefinition]:
        """
        Returns the definition of the given identifier.
        Returns None if it does not exist or not fully parsed.
        The alias mechanism is not used in this function.
        """
        if len(name) == 0:
            return None

        try:
            result = self.root.get(name)
        except MissingIdentifierError:
            return None

        if len(result.non_parsed) != 0:
            return None

        return result.identifier_definition

    def get_scope(self, name: ScopedName) -> 'IdentifierScope':
        """
        Finds the scope with the given name. Includes alias resolution.
        """
        current_identifier = name

        # Use a set of visited identifiers to detect cycles.
        visited_identifiers = []

        try:
            while current_identifier not in visited_identifiers:
                visited_identifiers.append(current_identifier)
                try:
                    # If current_identifier is a scope, return it.
                    return self.root.get_scope(current_identifier)
                except NotAScopeError as exc:
                    definition = exc.definition
                    non_parsed = exc.non_parsed
                    if not isinstance(definition, AliasDefinition):
                        raise

                # Resolve alias.
                current_identifier = definition.destination + non_parsed
        except IdentifierError as exc:
            # If there were no aliases, just raise the error unchanged.
            if len(visited_identifiers) == 1:
                raise
            # Add a prefix with the alias resolution.
            resolution_str = ' -> '.join(map(str, visited_identifiers))
            raise IdentifierError(f'Alias resolution failed: {resolution_str}. {exc}') from None

        # We found an alias cycle.
        cycle_str = ' -> '.join(map(str, visited_identifiers + [current_identifier]))
        raise IdentifierError(f'Cyclic aliasing detected: {cycle_str}')

    def _search(
            self, accessible_scopes: List[ScopedName],
            name: ScopedName, get_scope: bool) -> Union[IdentifierSearchResult, 'IdentifierScope']:
        """
        Searches an identifier (if get_scope=False) or a scope (if get_scope=True) in the given
        accessible scopes. Later scopes override the first ones.
        """
        # Later accessible scopes override the first ones.
        for scope in accessible_scopes[::-1]:
            try:
                if get_scope:
                    return self.get_scope(scope + name)
                else:
                    return self.get(scope + name)
            except MissingIdentifierError as exc:
                # If the problem is already with the first item in name (or in the scope itself),
                # just continue to the next accessible scope.
                # For example, if there are two accessible scopes: 'scope0' and 'scope1', and both
                # contain identifier named 'x'. If we are given 'x.y', we will only search for
                # 'scope0.x.y', not 'scope1.x.y'.
                # On the other hand if 'scope0' has no identifier 'x', we will look for
                # 'scope1.x.y'.
                if (scope + name[:1]).startswith(exc.fullname):
                    continue
                raise

        raise MissingIdentifierError(name[:1])

    def search(
            self, accessible_scopes: List[ScopedName], name: ScopedName) -> IdentifierSearchResult:
        """
        Searches an identifier in the given accessible scopes. Later scopes override the first ones.
        """
        res = self._search(accessible_scopes=accessible_scopes, name=name, get_scope=False)
        assert isinstance(res, IdentifierSearchResult)
        return res

    def search_scope(
            self, accessible_scopes: List[ScopedName], name: ScopedName) -> 'IdentifierScope':
        """
        Searches a scope in the given accessible scopes. Later scopes override the first ones.
        """
        res = self._search(accessible_scopes=accessible_scopes, name=name, get_scope=True)
        assert isinstance(res, IdentifierScope)
        return res

    def exclude(self, other: 'IdentifierManager') -> 'IdentifierManager':
        """
        Returns a copy of the identifier manager without the identifiers that exist in other.
        """
        other_as_dict = other.as_dict()
        return IdentifierManager.from_dict({
            name: value
            for name, value in self.as_dict().items()
            if name not in other_as_dict
        })

    def prune(self, prefixes_to_prune: Set[ScopedName]):
        """
        Removes identifiers that have one of the given prefixes.
        """
        # Prune dict.
        new_dict = {}
        for name, value in self.dict.items():
            parent = name
            while len(parent.path) > 0:
                if parent in prefixes_to_prune:
                    break
                parent = parent[:-1]
            if parent in prefixes_to_prune:
                assert isinstance(value, (IdentifierDefinition, FutureIdentifierDefinition)), \
                    f"Attempted to prune identifier '{value}'" \
                    f" of unprunable type '{type(value).__name__}'."
                continue
            new_dict[name] = value
        self.dict = new_dict

        # Remove scopes.
        for prefix in prefixes_to_prune:
            assert len(prefix.path) > 0
            current = self.root
            for element in prefix[:-1].path:
                current = current.subscopes[element]
            del current.subscopes[prefix.path[-1]]


class IdentifierScope:
    """
    Represents a scope of identifiers.
    """

    def __init__(self, manager: IdentifierManager, fullname: ScopedName):
        self.manager = manager
        self.fullname = fullname
        self.subscopes: Dict[str, IdentifierScope] = {}
        self.identifiers: Dict[str, IdentifierDefinition] = {}

    def add_identifier(self, name: ScopedName, definition: IdentifierDefinition):
        """
        Adds an identifier to the manager. name is relative to the current scope.
        """
        if len(name) == 0:
            raise ValueError('The name argument must not be empty.')

        first_name, non_parsed = name.path[0], name[1:]

        if len(name) == 1:
            self.identifiers[first_name] = definition
            self.manager.dict[self.fullname + first_name] = definition
            return

        if first_name not in self.subscopes:
            self.subscopes[first_name] = IdentifierScope(
                manager=self.manager, fullname=self.fullname + first_name)

        self.subscopes[first_name].add_identifier(non_parsed, definition)

    def get(self, name: ScopedName) -> IdentifierSearchResult:
        """
        Retrieves the identifer with the given name
        (possibly not fully parsed, without alias resolution).
        """
        assert len(name) > 0, "The 'name' argument must not be empty."

        first_name, non_parsed = name.path[0], name[1:]
        canonical_name = self.fullname + first_name

        if len(name) > 1 and first_name in self.subscopes:
            return self.subscopes[first_name].get(non_parsed)

        if first_name in self.identifiers:
            return IdentifierSearchResult(
                identifier_definition=self.identifiers[first_name],
                canonical_name=canonical_name,
                non_parsed=non_parsed)

        raise MissingIdentifierError(fullname=self.fullname + first_name)

    def get_scope(self, name: ScopedName) -> 'IdentifierScope':
        """
        Retrieves the scope with the given name.
        Raises NotAScopeError if name refers to an identifier rather than a scope
        (without alias resolution).
        """
        if len(name) == 0:
            return self
        first_name, non_parsed = name.path[0], name[1:]
        if first_name not in self.subscopes:
            fullname = self.fullname + first_name
            if first_name in self.identifiers:
                raise NotAScopeError(
                    fullname=fullname, definition=self.identifiers[first_name],
                    non_parsed=non_parsed)
            else:
                raise MissingIdentifierError(fullname=fullname)
        return self.subscopes[first_name].get_scope(non_parsed)
