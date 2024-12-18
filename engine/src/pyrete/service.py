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
    service_id = f"{repository.id}:{int(round(time() * 1000))}"
    logging.debug("Executing service: %s", service_id)
    resulting_facts = facts
    for ruleset in repository.rulesets:
        if start_from and ruleset.id != start_from:
            continue
        logging.debug("Creating session with service Id: %s, ruleset:%s, facts:%s", service_id, ruleset, facts)
        session = Session(ruleset, resulting_facts, f"{service_id}:{ruleset.id}", global_ctx)
        resulting_facts = session.execute()
        logging.debug("Executed session: %s", session)
        if switch_to := __find_switch(resulting_facts):
            resulting_facts.remove(switch_to)
            if switch_to.ruleset == '_end':
                break
            return execute(repository, resulting_facts, global_ctx, switch_to.ruleset)
    logging.debug("Executed service: %s", service_id)
    return resulting_facts