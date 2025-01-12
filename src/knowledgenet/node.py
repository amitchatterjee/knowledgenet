import logging
from types import SimpleNamespace

from knowledgenet.tracer import trace

class Leaf:
    def __init__(self, id, rule, when_index):
        self.id = id
        self.rule = rule
        self.when_index = when_index
        self.executed = False

    @trace()
    def execute(self, context, fact):
        if self.executed:
            # Return the previous result
            return True, self.result
        # Else, evaluate the expression
        if self.rule.whens[self.when_index].var:
            setattr(context, self.rule.whens[self.when_index].var, fact)
        self.result = True 
        for each_exp in self.rule.whens[self.when_index].matches:
            self.result = self.result and each_exp(context, fact)
            if not self.result:
                break
        self.executed = True
        return False, self.result
    
    def __str__(self):
        return f"Leaf({self.id})"

    def __repr__(self):
        return self.__str__()

class Node:
    def __init__(self, id, rule, graph, global_ctx, when_objs):
        self.id = id
        self.rule = rule
        self.graph = graph
        self.global_ctx = global_ctx
        self.when_objs = when_objs
        self.context = None
        self.changes = None

        # Create when expression execution context
        self.leaves = []
        for i, when in enumerate(rule.whens):
            self.leaves.append(Leaf(f"{self.id}[{i}]", rule, i))

    @trace()
    def reset_whens(self, updated_facts:set)->bool:
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
    def execute(self, facts_set:set)->dict:
        # Create an empty context for when expressions to populate stuff with
        # Add all "facts" to this context. This will be used by accumulator and other DSL methods

        if not self.context:
            self.context = SimpleNamespace(_facts=facts_set, _node=self, _graph=self.graph, _global=self.global_ctx)
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