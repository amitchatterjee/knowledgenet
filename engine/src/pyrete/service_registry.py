from ruleset import Ruleset
from service import Service

registry={}

def lookup(service_id, global_ctx={}):
    if service_id not in registry:
        raise Exception('service not found')
    rulesets=[]
    for ruleset_id, rules in registry[service_id].items():
        rulesets.append(Ruleset(ruleset_id, rules))
    # Sort by id. The assumption is that the ids are defined in such a way that order can be determined. For example: 001-validation-rules, 002-business-rules, etc.
    rulesets.sort(key=lambda e: e.id)
    return Service(service_id, rulesets, global_ctx=global_ctx)