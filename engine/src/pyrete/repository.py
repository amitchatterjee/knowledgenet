from ruleset import Ruleset

registry={}

def lookup(repository:str):
    if repository not in registry:
        raise Exception('repository not found')
    rulesets=[]
    for ruleset_id, rules in registry[repository].items():
        rulesets.append(Ruleset(ruleset_id, rules))
    # Sort by id. The assumption is that the ids are defined in such a way that order can be determined. For example: 001-validation-rules, 002-business-rules, etc.
    rulesets.sort(key=lambda e: e.id)
    return Repository(repository, rulesets)

class Repository:
    def __init__(self, id:str, rulesets:list[Ruleset]):
        self.id = id
        self.rulesets = rulesets

    def __str__(self):
        return f"Repository({self.id})"
    
    def __repr__(self):
        return self.__str__()
