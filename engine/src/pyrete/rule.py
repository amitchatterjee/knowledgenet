from util import to_list
from knowledge_registry import registry

class Rule:
    def __init__(self, id, when, then, order=0, knowledge=None, ruleset=None, **kwargs):
        self.id = id
        self.order = order
        self.whens = to_list(when)
        self.thens = to_list(then)
        for key, value in kwargs.items():
            setattr(self, key, value)
        # TODO add validations
        if (knowledge and not ruleset) or (ruleset and not knowledge):
            raise Exception('Both "knowledge" and "ruleset" must be specified')
        if knowledge:
            if knowledge not in registry:
                registry[knowledge] = {}
            if ruleset not in registry[knowledge]:
                registry[knowledge][ruleset] = []
            registry[knowledge][ruleset].append(self)

    def __str__(self):
        return f"Rule({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name

class Condition:
    def __init__(self, for_type, matches_exp):
        self.for_type = for_type
        self.exp = matches_exp
        # TODO add validation
