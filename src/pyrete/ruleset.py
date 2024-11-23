from pyrete.session import Session

class Ruleset:
    def __init__(self, name, rules, globals=[]):
        self.name = name
        # TODO add rule validations
        self.rules = rules
        self.globals = globals

