from typing import Callable, Union

from knowledgenet.util import to_frozenset, to_tuple

class Switch:
    def __init__(self, ruleset:str):
        self.ruleset = ruleset
    def __str__(self):
        return f"Switch({self.ruleset})"
    def __repr__(self):
        return self.__str__()

class EventFact:
    def __init__(self, on_types:Union[list[type],tuple[type],set[type],frozenset[type],type], **kwargs):
        self.on_types = to_frozenset(on_types)
        for key,value in kwargs.items():
            setattr(self, key, value)
        self.reset()

    def reset(self):
        self.added = set()
        self.updated = set()
        self.deleted = set()

    def __str__(self):
        return f"EventFact({[each.__name__ for each in self.on_types]})"
    def __repr__(self):
        return self.__str__()
    def __hash__(self):
        return hash(self.on_types)
    def __eq__(self, other):
        if isinstance(other, EventFact):
            return self.__hash__() == other.__hash__()
        return False

class Wrapper:
    # TODO - implement a wrapper engine and support for this class.
    '''Wrapper class for Facts. When dealing with large fact objects - having all the large facts in memory may not be a viable option. To deal with this problem, we can use a wrapper. The wrapper stores a uniqueue id only instead of the whole object. The wrapper engine associated with the rule engine will be responsible for fetching and writing the object when needed.
    '''
    def __init__(self, of_type:type, id:str, var:str=None,
                 matches:Union[list[callable],tuple[callable],callable]=lambda ctx,this:True):
        self.of_type = of_type
        self.id = id
        self.matches = to_tuple(matches)
        self.var = var

    def __str__(self):
        return str(self.id)
    
    def __repr__(self):
        return self.__str__()
