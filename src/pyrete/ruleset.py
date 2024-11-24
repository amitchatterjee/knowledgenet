from pyrete.session import Session

class Ruleset:
    def __init__(self, id, rules, globals=[]):
        self.id = id
        # TODO add rule validations
        self.rules = rules
        self.globals = globals

    def __str__(self):
        return f"Ruleset({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
