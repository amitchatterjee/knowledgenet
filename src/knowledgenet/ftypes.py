import hashlib
from typing import Callable, Union

from knowledgenet.container import Collector
from knowledgenet.util import to_tuple

class Switch:
    def __init__(self, ruleset: str):
        self.ruleset = ruleset
    def __str__(self):
        return f"Switch({self.ruleset})"
    def __repr__(self):
        return self.__str__()

class EventFact:
    def __init__(self, group: str, on_types: list[type] | tuple[type] | set[type] | type, **kwargs):
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

    def reset(self):
        self.added = set()
        self.updated = set()
        self.deleted = set()

    def __str__(self):
        return f"EventFact({self.group}, args={self._init_args}, types={[each.__name__ for each in self.on_types]})"
    def __repr__(self):
        return self.__str__()
    def __hash__(self):
        return self._int_hash
    def __eq__(self, other):
        if isinstance(other, EventFact):
            return self.__hash__() == other.__hash__()
        return False

class Wrapper:
    def __init__(self, of_type: str | type,  **kwargs):
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

    def __str__(self):
        descriptor = f"name={self.init_args['name']}" if 'name' in self._init_args else f"args={self._init_args}"
        return f"Wrapper({self.of_type}, {descriptor})"
    def __repr__(self):
        return self.__str__()
    def __hash__(self):
        return self._int_hash
    def __eq__(self, other):
        if isinstance(other, Wrapper):
            return self.__hash__() == other.__hash__()
        return False