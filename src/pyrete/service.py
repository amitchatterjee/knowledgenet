from pyrete.session import Session

class Service:
    def __init__(self, id, rulesets, globals=[]):
        self.id = id
        self.rulesets = rulesets
        self.globals = globals

    def execute(self, facts):
        resulting_facts = facts
        for ruleset in self.rulesets:
            session = Session(ruleset, resulting_facts, self.globals)
            resulting_facts = session.execute()
        return resulting_facts

    def __str__(self):
        return f"Service(ruleset: {self.ruleset})"
    
    def __repr__(self):
        return self.__str__()
