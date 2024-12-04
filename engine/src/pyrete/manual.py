from session import Session
import uuid

class Manual:
    def __init__(self, id, rulesets):
        self.id = id
        self.rulesets = rulesets

    def __str__(self):
        return f"Manual(rulesets: {self.rulesets})"
    
    def __repr__(self):
        return self.__str__()
