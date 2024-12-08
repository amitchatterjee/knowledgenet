from typing import Union
from util import to_list

class Condition:
    def __init__(self, of_type:type, matches_exp:callable):
        self.of_type = of_type
        self.exp = matches_exp
        # TODO add validation

class Rule:
    def __init__(self, id:str, when:Union[list[Condition],Condition], then:Union[list[callable],callable], 
                 order=0, merges:list[type]=None, repository:str=None, ruleset:str=None, 
                 run_once=False, retrigger_on_update=True, **kwargs):
        from repository import registry
        self.id = id
        self.order = order
        self.merges = merges
        self.whens = to_list(when)
        self.thens = to_list(then)
        self.run_once = run_once
        self.retrigger_on_update = retrigger_on_update
        for key, value in kwargs.items():
            setattr(self, key, value)
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
        return f"Rule({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
