from pyrete.session import Session
import uuid

class Service:
    def __init__(self, id, rulesets, global_ctx=[]):
        self.id = id
        self.rulesets = rulesets
        self.global_ctx = global_ctx

    def execute(self, facts):
        resulting_facts = facts
        for ruleset in self.rulesets:
            session = Session(ruleset, resulting_facts, f"{self.id}-{uuid.uuid1()}", self.global_ctx)
            resulting_facts = session.execute()
        return resulting_facts

    def __str__(self):
        return f"Service(ruleset: {self.ruleset})"
    
    def __repr__(self):
        return self.__str__()
