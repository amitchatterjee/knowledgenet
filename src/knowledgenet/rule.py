from typing import Union
import uuid

from knowledgenet.ftypes import EventFact
from knowledgenet.util import to_frozenset, to_list, to_tuple
from knowledgenet.container import Collector

class Event:
    def __init__(self, group,
                 matches:Union[list[callable],tuple[callable],callable]=lambda ctx,this:True, var:str=None,):
        self.group = group
        self.var = var
        self.matches = matches

class Collection:
    def __init__(self, group:str, matches:Union[list[callable],tuple[callable],callable]=lambda ctx,this:True, var:str=None):
        self.group = group
        self.matches = to_tuple(matches)
        self.var = var

# AI-generated code: Change the highlighted typedef code to python 3.14 using | instead of Union
class Fact:
    def __init__(self, of_type:Union[type,str], 
                 matches:Union[list[callable],tuple[callable],callable]=lambda ctx,this:True, 
                 group=None, var:str=None, **kwargs):
        if of_type in [Collector, EventFact] and not group:
            # This situation will only occur if the rule is not using the syntaic sugar syntax
            raise Exception("when of_type is Collector, group must be specified")
        self.of_type = of_type
        self.matches = to_tuple(matches)
        self.group = group
        self.var = var
        for key, value in kwargs.items():
            setattr(self, key, value)

class Rule:
    def __init__(self, id:str=None, 
                 when:Union[list[Union[Fact,Collection]],tuple[Union[Fact,Collection]],Union[Fact,Collection]]=(), 
                 then:Union[list[callable],tuple[callable],callable]=lambda ctx: None, 
                 order=0, merges:list[type]=None, 
                 run_once=False, retrigger_on_update=True, **kwargs):
        self.id = id if id else uuid.uuid4()
        self.order = order
        self.merges = merges
        self.whens = self._preprocess_whens(when)
        self.thens = to_tuple(then)
        self.run_once = run_once
        self.retrigger_on_update = retrigger_on_update
        # The following properties are for external rule management entities like scanner, etc.
        for key,value in kwargs.items():
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
