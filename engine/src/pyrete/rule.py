from typing import Union

from util import to_tuple
from ftypes import Collector

class Condition:
    def __init__(self, of_type:type, matches_exp:callable, group=None):
        if of_type == Collector and not group:
            raise Exception("when of_type is Collector, id must be specified")
        # TODO add more validations
        self.of_type = of_type
        self.exp = matches_exp
        self.group = group

class Rule:
    def __init__(self, id:str, when:Union[list[Condition],tuple[Condition],Condition], 
                 then:Union[list[callable],tuple[callable],callable], 
                 order=0, merges:list[type]=None, repository:str=None, ruleset:str=None, 
                 run_once=False, retrigger_on_update=True):
        from repository import registry
        self.id = id
        self.order = order
        self.merges = merges
        self.whens = to_tuple(when)
        self.thens = to_tuple(then)
        self.run_once = run_once
        self.retrigger_on_update = retrigger_on_update
        
        # TODO add validations
        if (repository and not ruleset) or (ruleset and not repository):
            raise Exception('Both "repository" and "ruleset" must be specified')
        if repository:
            if repository not in registry:
                registry[repository] = {}
            if ruleset not in registry[repository]:
                registry[repository][ruleset] = []
            registry[repository][ruleset].append(self)

    def __str__(self):
        return f"Rule({self.id}, order:{self.order})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
