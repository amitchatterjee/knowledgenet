from typing import Union
import uuid

from knowledgenet.util import to_tuple
from knowledgenet.collector import Collector

class Fact:
    def __init__(self, of_type:type, matches:callable, group=None):
        if of_type == Collector and not group:
            raise Exception("when of_type is Collector, id must be specified")
        # TODO add more validations
        self.of_type = of_type
        self.exp = matches
        self.group = group

class Rule:
    def __init__(self, id:str=None, when:Union[list[Fact],tuple[Fact],Fact]=(), 
                 then:Union[list[callable],tuple[callable],callable]=lambda ctx: None, 
                 order=0, merges:list[type]=None, 
                 run_once=False, retrigger_on_update=True, **kwargs):
        # TODO add validations
        self.id = id if id else uuid.uuid4()
        self.order = order
        self.merges = merges
        self.whens = to_tuple(when)
        self.thens = to_tuple(then)
        self.run_once = run_once
        self.retrigger_on_update = retrigger_on_update
        # The following properties are for external rule management entities like scanner, etc.
        for key,value in kwargs.items():
            setattr(self, key, value)

        self.ordinal = 0

    def __str__(self):
        return f"Rule({self.id}, order:{self.order})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
