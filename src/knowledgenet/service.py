import inspect
from time import time
import logging
from contextvars import ContextVar
import json

from knowledgenet.core.session import Session
from knowledgenet.ftypes import Switch
from knowledgenet.core.tracer import timestamp, trace

trace_method = ContextVar('trace_method', default=None)
trace_buffer = ContextVar('trace_buffer', default=None)

class Service:
    def __init__(self, repository, id="knowledgenet", global_ctx={}):
        self.id = id
        self.repository = repository
        self.global_ctx = global_ctx

    def __str__(self):
        return f"Service({self.repository.id})"
    
    def __repr__(self):
        return self.__str__()

    def _find_switch(self, facts):
        for fact in facts:
            if isinstance(fact, Switch):
                return fact
        return None

    def execute(self, facts, start_from=None, trc_method=None, trc_stream=None):
        trace_method.set(trc_method)
        if trc_stream:
            trace_buffer.set([])
        try:
            return self._execute_service(facts, start_from)
        finally:
            if trc_stream:
                root = {'obj': f"{self.id}",
                    'func': f"{type(self).__name__}.{inspect.currentframe().f_code.co_name}",
                    'args': list(map(lambda e: str(e), 
                                inspect.getargvalues(inspect.currentframe().f_back).locals.values()[1:])),
                    'kwargs': None,
                    'start': timestamp(),
                    'calls': trace_buffer.get()
                }
                json.dump(root, trc_stream, indent=2)
                trace_buffer.set(None)
                trace_method.set(None)
 
    @trace()
    def _execute_service(self, facts, start_from):
        service_id = f"{self.repository.id}:{int(round(time() * 1000))}"
        logging.debug("Executing service: %s", service_id)
        resulting_facts = facts
        for ruleset in self.repository.rulesets:
            if start_from and ruleset.id != start_from:
                continue
            logging.debug("Creating session with service Id: %s, ruleset:%s, facts:%s", service_id, ruleset, resulting_facts)
            session = Session(ruleset, resulting_facts, f"{service_id}:{ruleset.id}", self.global_ctx)
            resulting_facts = session.execute()
            logging.debug("Executed session: %s", session)
            if switch_to := self._find_switch(resulting_facts):
                resulting_facts.remove(switch_to)
                if not switch_to.ruleset:
                    break
                return self._execute_service(resulting_facts, switch_to.ruleset)
        logging.debug("Executed service: %s", service_id)
        return resulting_facts