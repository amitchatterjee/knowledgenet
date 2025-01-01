from knowledgenet.ruleset import Ruleset

class Repository:
    def __init__(self, id:str, rulesets:list[Ruleset]):
        self.id = id
        self.rulesets = rulesets
        # Sort by id. The assumption is that the ids are defined in alphabetical order. For example: 001-validation-rules, 002-business-rules, etc.
        self.rulesets.sort(key=lambda r: r.id)

    def __str__(self):
        return f"Repository({self.id})"
    
    def __repr__(self):
        return self.__str__()
