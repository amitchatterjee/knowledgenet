from ruleset import Ruleset
from manual import Manual

registry={}

def lookup(manual_id):
    if manual_id not in registry:
        raise Exception('manual not found')
    rulesets=[]
    for ruleset_id, rules in registry[manual_id].items():
        rulesets.append(Ruleset(ruleset_id, rules))
    # Sort by id. The assumption is that the ids are defined in such a way that order can be determined. For example: 001-validation-rules, 002-business-rules, etc.
    rulesets.sort(key=lambda e: e.id)
    return Manual(manual_id, rulesets)