from session import Session
from ftypes import Switch
from time import time
import logging

def __find_switch(facts):
    for fact in facts:
        if isinstance(fact, Switch):
            return fact
    return None
        
def execute(repository, facts, global_ctx={}, start_from=None):
    service_id = int(round(time() * 1000))
    logging.debug(f"Executing service: {service_id}")
    resulting_facts = facts
    for ruleset in repository.rulesets:
        if start_from and ruleset.id != start_from:
            continue
        logging.debug(f"Creating session with service Id: {service_id}, ruleset: {ruleset}, facts:{facts}")
        session = Session(ruleset, resulting_facts, f"{repository.id}:{ruleset.id}:{service_id}", global_ctx)
        resulting_facts = session.execute()
        logging.debug(f"Executed session: {session}")
        if switch_to := __find_switch(resulting_facts):
            resulting_facts.remove(switch_to)
            if switch_to.ruleset == '_end':
                break
            return execute(repository, resulting_facts, global_ctx, switch_to.ruleset)
    logging.debug(f"Executed service: {service_id}")
    return resulting_facts