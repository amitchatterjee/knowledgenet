from util import to_list
from repository import registry

class Rule:
    def __init__(self, id, when, then, order=0, merges = None, repository=None, ruleset=None, 
                 run_once=False, retrigger=True, **kwargs):
        self.id = id
        self.order = order
        self.merges = merges
        self.whens = to_list(when)
        self.thens = to_list(then)
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

class Condition:
    def __init__(self, of_type, matches_exp):
        self.of_type = of_type
        self.exp = matches_exp
        # TODO add validation
