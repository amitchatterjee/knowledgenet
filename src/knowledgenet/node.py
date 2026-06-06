"""Runtime node execution primitives.

Nodes are concrete rule instances bound to one matched fact combination.
Leaves cache individual when-clause evaluation outcomes to avoid recomputing
unchanged predicates after updates.
"""

import logging
from types import SimpleNamespace

from knowledgenet.core.tracer import trace

class Leaf:
    """Evaluator for one when-clause bound to one fact object.

    Leaf instances cache their last result and are selectively invalidated by
    session update processing.
    """

    def __init__(self, id, rule, when_index):
        self.id = id
        self.rule = rule
        self.when_index = when_index
        self.executed = False

    @trace()
    def execute(self, context, fact):
        """Evaluate one when-clause and optionally use cached result.

        Returns:
            tuple[bool, bool]: ``(cached, result)`` where ``cached`` indicates
            whether evaluation was skipped due to cache hit.
        """
        if self.executed:
            # Return the previous result
            return True, self.result
        # Else, evaluate the expression
        if self.rule.whens[self.when_index].var:
            setattr(context, self.rule.whens[self.when_index].var, fact)
        self.result = True 
        for match in self.rule.whens[self.when_index].matches:
            self.result = self.result and match(context, fact)
            if not self.result:
                break
        self.executed = True
        return False, self.result
    
    def __str__(self):
        return f"Leaf({self.id})"

    def __repr__(self):
        return self.__str__()

class Node:
    """Concrete runtime instance of a rule.

    A node binds a Rule to one combination of when-clause objects and manages
    predicate evaluation plus then-action execution for that binding.
    """

    def __init__(self, id, rule, session, when_objs):
        self.id = id
        self.rule = rule
        self.session = session
        self.when_objs = when_objs
        self.context = None
        self.changes = None

        # Create when expression execution context
        self.leaves = []
        for i, when in enumerate(rule.whens):
            self.leaves.append(Leaf(f"{self.id}[{i}]", rule, i))

    @trace(level=13)
    def reset_whens(self, updated_facts:set)->bool:
        """Invalidate cached leaves after fact updates.

        If any bound when object is updated, this method clears cache from that
        position to the end to preserve ordered predicate dependencies.
        """
        found = False
        for i,leaf in enumerate(self.when_objs):
            if leaf in updated_facts:
                # clear cache from the leaves for the leaf + everything after it
                for j in range(i, len(self.when_objs)):
                    leaf = self.leaves[j]
                    leaf.executed = False
                    leaf.result = None
                return True
        return False

    @trace()
    def execute(self, facts:set)->dict:
        """Execute this node against current facts.

        The method evaluates leaves in rule order, uses cached leaf outcomes
        when possible, and executes then-actions only when all predicates pass
        and at least one leaf was evaluated non-cached.

        Returns:
            bool: True when then actions executed, False otherwise.
        """
        # Create an empty context for when expressions to populate stuff with
        # Add all "facts" to this context. This will be used by accumulator and other DSL methods

        if not self.context:
            self.context = SimpleNamespace(_facts=facts, _node=self, _session=self.session)
        self.context._changes={}
        
        all_cached = True
        # Evaluate all when clauses
        for i, when in enumerate(self.leaves):
            cached, result = when.execute(self.context, self.when_objs[i])
            logging.debug("%s: Executed when expression for index: %d, cached/result: %s:%s", self, i, cached, result) 
            all_cached = all_cached and cached
            if not result:
                return False

        # If all the executions were cached, there is no need to execute the then
        if all_cached:
            return False
        
        # If we are here, it means all the when conditions were satisfied, execute the then expression
        logging.debug("%s: All when clauses satisfied, going to execute the then clauses", self)
        self.changes = self._execute_thens()
        logging.debug("%s: Result from when execution. Changes:%s", self, self.changes)
        return True

    @trace()
    def _execute_thens(self):
        for then in self.rule.thens:
            # Execute each function/lambda included in the rule
            then(self.context)
        return self.context._changes

    def __str__(self):
        return f"Node({self.id}, rule:{self.rule}, whens:{self.when_objs})"

    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
      return self.id == other.id