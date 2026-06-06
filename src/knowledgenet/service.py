"""Service entrypoint for transactional RETE execution.

The service coordinates end-to-end execution of a repository, where each
ruleset is executed in its own runtime session. Facts emitted from one session
become inputs to the next session unless flow-control facts change the path.
"""

from time import time
import logging
from contextvars import ContextVar

from knowledgenet.core.session import Session
from knowledgenet.ftypes import Switch
from knowledgenet.core.tracer import trace

trace_level = ContextVar('trace_level', default=0)
trace_details = ContextVar('trace_details', default=0)

class Service:
    """Coordinates repository execution across rulesets.

    A service is typically initialized once during application startup and
    reused for many transactions. Each call to :meth:`execute` processes one
    transaction and returns the final fact set produced by chained rulesets.
    """

    def __init__(self, repository, id="knowledgenet", global_ctx={}, node_sorter=None):
        self.id = id
        self.repository = repository
        self.global_ctx = global_ctx
        self.node_sorter = node_sorter

    def __str__(self):
        return f"Service({self.repository.id})"
    
    def __repr__(self):
        return self.__str__()

    def _find_switch(self, facts):
        for fact in facts:
            if isinstance(fact, Switch):
                return fact
        return None

    def execute(self, facts, start_from=None, trc_level=0, trc_details=0):
        """Execute a transaction against the repository.

        Args:
            facts: Initial transaction facts.
            start_from: Optional ruleset id to start from instead of the first
                repository ruleset.
            trc_level: Runtime trace verbosity threshold.
            trc_details: Runtime trace payload detail level.

        Returns:
            Final set of facts after all reachable rulesets complete.

        Examples:
            Basic transaction execution::

                result_facts = Service(repo).execute([C1(10), C1(20)])

            Resume execution from a specific ruleset::

                result_facts = Service(repo).execute(facts, start_from='rs2')
        """
        trace_level.set(trc_level)
        trace_details.set(trc_details)
        return self._execute_service(facts, start_from)
 
    @trace()
    def _execute_service(self, facts, start_from):
        service_id = f"{self.repository.id}:{int(round(time() * 1000))}"
        logging.debug("Executing service: %s", service_id)
        resulting_facts = facts
        for ruleset in self.repository.rulesets:
            if start_from and ruleset.id != start_from:
                continue
            logging.debug("Creating session with service Id: %s, ruleset:%s, facts:%s", service_id, ruleset, resulting_facts)
            session = Session(ruleset, resulting_facts, f"{service_id}:{ruleset.id}", 
                              self.global_ctx, self.node_sorter)
            resulting_facts = session.execute()
            logging.debug("Executed session: %s", session)
            if switch_to := self._find_switch(resulting_facts):
                resulting_facts.remove(switch_to)
                if not switch_to.ruleset:
                    break
                return self._execute_service(resulting_facts, switch_to.ruleset)
        logging.debug("Executed service: %s", service_id)
        return resulting_facts