from session import Session
from ftypes import Switch
from time import time
import logging

class Service:
    def __init__(self, repository,  global_ctx={}):
        self.repository = repository
        self.global_ctx = global_ctx

    def __str__(self):
        return f"Service({self.repository.id})"
    
    def __repr__(self):
        return self.__str__()

    def __find_switch(self, facts):
        for fact in facts:
            if isinstance(fact, Switch):
                return fact
        return None
            
    def execute(self, facts, start_from=None):
        service_id = f"{self.repository.id}:{int(round(time() * 1000))}"
        logging.debug("Executing service: %s", service_id)
        resulting_facts = facts
        for ruleset in self.repository.rulesets:
            if start_from and ruleset.id != start_from:
                continue
            logging.debug("Creating session with service Id: %s, ruleset:%s, facts:%s", service_id, ruleset, facts)
            session = Session(ruleset, resulting_facts, f"{service_id}:{ruleset.id}", self.global_ctx)
            resulting_facts = session.execute()
            logging.debug("Executed session: %s", session)
            if switch_to := self.__find_switch(resulting_facts):
                resulting_facts.remove(switch_to)
                if switch_to.ruleset == '_end':
                    break
                return self.execute(resulting_facts, switch_to.ruleset)
        logging.debug("Executed service: %s", service_id)
        return resulting_facts