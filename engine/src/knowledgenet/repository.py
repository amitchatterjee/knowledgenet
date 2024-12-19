from ruleset import Ruleset

class Repository:
    def __init__(self, id:str, rulesets:list[Ruleset]):
        self.id = id
        self.rulesets = rulesets

    def __str__(self):
        return f"Repository({self.id})"
    
    def __repr__(self):
        return self.__str__()
