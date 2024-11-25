from pyrete.ruleset import Ruleset
from pyrete.service import Service
registry={}

def lookup(service_id, global_ctx={}):
    if service_id not in registry:
        raise Exception('service not found')
    rulesets=[]
    # TODO, the order of the rulesets need to be specified
    for ruleset_id, rules in registry[service_id].items():
        rulesets.append(Ruleset(ruleset_id, rules))
    return Service(service_id, rulesets, global_ctx=global_ctx)