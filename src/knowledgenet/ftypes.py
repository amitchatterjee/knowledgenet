"""Infrastructure fact types used by the runtime and rule DSL."""

import hashlib

from knowledgenet.container import Collector
from knowledgenet.util import to_tuple

class Switch:
    """Control-flow fact used to redirect service execution.

    A ``Switch`` fact is emitted by control helpers and consumed by
    :class:`knowledgenet.service.Service` after each ruleset session.
    """

    def __init__(self, ruleset: str | None) -> None:
        self.ruleset = ruleset
    def __str__(self) -> str:
        return f"Switch({self.ruleset})"
    def __repr__(self) -> str:
        return self.__str__()

class EventFact:
    """Tracks added, updated, and deleted facts for one event group.

    EventFact is updated by Factset when matching domain facts change and can
    be matched in rules through ``Event(...)`` or ``Fact(of_type=EventFact)``.

    Example:
        Monitor inserts/updates/deletes of C1 facts::

            EventFact(group='c1-events', on_types=C1)
    """

    def __init__(self, group: str, on_types: list[type] | tuple[type] | set[type] | type, **kwargs: object) -> None:
        self.on_types = to_tuple(on_types)
        if Collector in self.on_types or EventFact in self.on_types:
            raise Exception("EventFact on_types cannot contain Collector or EventFact")
        self.group = group
        self._init_args = kwargs
        for key,value in kwargs.items():
            setattr(self, key, value)
        self.reset()
        hasher = hashlib.sha256(group.encode())
        hasher.update(str(on_types).encode())
        for key,value in sorted(kwargs.items()):
            hasher.update(str(key).encode())
            hasher.update(str(value).encode())
        self._int_hash = int(hasher.hexdigest(), 16)

    def reset(self) -> None:
        """Clear accumulated change buckets for this event cycle."""
        self.added: set = set()
        self.updated: set = set()
        self.deleted: set = set()

    def __str__(self) -> str:
        return f"EventFact({self.group}, args={self._init_args}, types={[each.__name__ for each in self.on_types]})"
    def __repr__(self) -> str:
        return self.__str__()
    def __hash__(self) -> int:
        return self._int_hash
    def __eq__(self, other: object) -> bool:
        if isinstance(other, EventFact):
            return self.__hash__() == other.__hash__()
        return False

class Wrapper:
    """Named or typed wrapper fact for lightweight context injection.

    Wrapper is commonly used to provide ruleset-scoped configuration and other
    structured context without introducing dedicated domain classes.

    Example:
        Wrap a domain fact for named matching or collector aggregation::

            Wrapper(of_type='wrapper', wraps=C1(10))
    """

    def __init__(self, of_type:str|type|None=None, named:str|None=None, **kwargs: object) -> None:
        if not named and not of_type:
            raise Exception('Either type or named must be specified')
        
        if named and of_type:
            raise Exception('type and named cannot be specified together')
        
        of_type = named if named else of_type
        # By construction, exactly one of named/of_type was truthy above, so
        # of_type is never None here -- the raises above guarantee it.
        assert of_type is not None

        self.of_type = of_type
        self._init_args = kwargs
        for key,value in kwargs.items():
            setattr(self, key, value)
        
        hasher = hashlib.sha256()
        if isinstance(of_type, str):
            hasher.update(of_type.encode())
        else:
            hasher.update(of_type.__name__.encode())
        for key,value in sorted(kwargs.items()):
            hasher.update(str(key).encode())
            hasher.update(str(value).encode())
        self._int_hash = int(hasher.hexdigest(), 16)

    def __str__(self) -> str:
        descriptor = f"name={self._init_args['name']}" if 'name' in self._init_args else f"args={self._init_args}"
        return f"Wrapper({self.of_type}, {descriptor})"
    def __repr__(self) -> str:
        return self.__str__()
    def __hash__(self) -> int:
        return self._int_hash
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Wrapper):
            return self.__hash__() == other.__hash__()
        return False