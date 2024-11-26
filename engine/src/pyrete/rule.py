from util import to_list
from service_registry import registry

class Rule:
    def __init__(self, id, when, then, order=0, service=None, ruleset=None, **kwargs):
        self.id = id
        self.order = order
        self.whens = to_list(when)
        self.thens = to_list(then)
        for key, value in kwargs.items():
            setattr(self, key, value)
        # TODO add validations
        if (service and not ruleset) or (ruleset and not service):
            raise Exception('Both "service" and "ruleset" must be specified')
        if service:
            if service not in registry:
                registry[service] = {}
            if ruleset not in registry[service]:
                registry[service][ruleset] = []
            registry[service][ruleset].append(self)

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
