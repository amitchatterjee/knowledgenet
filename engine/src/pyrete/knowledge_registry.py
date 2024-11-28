from ruleset import Ruleset
from knowledge import Knowledge

registry={}

def lookup(knowledge_id):
    if knowledge_id not in registry:
        raise Exception('knowledge not found')
    rulesets=[]
    for ruleset_id, rules in registry[knowledge_id].items():
        rulesets.append(Ruleset(ruleset_id, rules))
    # Sort by id. The assumption is that the ids are defined in such a way that order can be determined. For example: 001-validation-rules, 002-business-rules, etc.
    rulesets.sort(key=lambda e: e.id)
    return Knowledge(knowledge_id, rulesets)