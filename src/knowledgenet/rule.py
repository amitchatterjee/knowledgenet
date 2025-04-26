from typing import Callable
import uuid

from knowledgenet.ftypes import EventFact
from knowledgenet.util import to_list, to_tuple
from knowledgenet.container import Collector

class Event:
    def __init__(self, group,
                 matches: list[Callable] | tuple[Callable] | Callable = lambda ctx, this: True, 
                 var: str | None = None):
        self.group = group
        self.var = var
        self.matches = matches

class Collection:
    def __init__(self, group: str, 
                 matches: list[Callable] | tuple[Callable] | Callable = lambda ctx, this: True, 
                 var: str | None = None):
        self.group = group
        self.matches = to_tuple(matches)
        self.var = var

class Fact:
    def __init__(self, of_type: type | str = None, named: str = None, 
                 matches: list[Callable] | tuple[Callable] | Callable = lambda ctx, this: True, 
                 group=None, var: str | None = None, **kwargs):
        if not named and not of_type:
            raise Exception('Either type or named must be specified')
        
        if named and of_type:
            raise Exception('type and named cannot be specified together')
        
        of_type = named if named else of_type

        if of_type in [Collector, EventFact] and not group:
            raise Exception("when of_type is Collector or EventFact, group must be specified")
        self.of_type = of_type
        self.matches = to_tuple(matches)
        self.group = group
        self.var = var
        for key, value in kwargs.items():
            setattr(self, key, value)

class Rule:
    def __init__(self, id: str | None = None, 
                 when: list[Fact | Collection] | tuple[Fact | Collection] | Fact | Collection = (), 
                 then: list[Callable] | tuple[Callable] | Callable = lambda ctx: None, 
                 order=0, 
                 run_once=False, retrigger_on_update=True, **kwargs):
        self.id = id if id else uuid.uuid4()
        self.order = order
        self.whens = self._preprocess_whens(when)
        self.thens = to_tuple(then)
        self.run_once = run_once
        self.retrigger_on_update = retrigger_on_update
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _preprocess_whens(self, whens):
        whens = to_list(whens)
        for i, when in enumerate(whens):
            if type(when) == Collection:
                whens[i] = Fact(of_type=Collector, group=when.group, matches=when.matches, var=when.var)
            elif type(when) == Event:
                whens[i] = Fact(of_type=EventFact, group=when.group, matches=when.matches, var=when.var)
            elif type(when) != Fact:
                raise Exception('When clause must only contain Fact, Event and Collection types')
        return to_tuple(whens) 

    def __str__(self):
        return f"Rule({self.id}, order:{self.order})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
