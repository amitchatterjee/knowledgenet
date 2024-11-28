import logging

from types import SimpleNamespace

class Leaf:
    def __init__(self, rule, when_index):
        self.rule = rule
        self.when_index = when_index
        self.executed = False

    def execute(self, context, this):
        if self.executed:
            # Return the previous result
            return True, self.result
        # Else, evaluate the expression
        self.result = self.rule.whens[self.when_index].exp(context, this)
        self.executed = True
        return False, self.result

class Node:
    def __init__(self, id, rule, rules, global_ctx, when_objs):
        self.id = id
        self.rule = rule
        self.rules = rules
        self.global_ctx = global_ctx
        self.when_objs = when_objs

        # Create when expression execution context
        self.leaves = []
        for i, when in enumerate(rule.whens):
            self.leaves.append(Leaf(rule, i))

    def invalidate_leaves(self, updated_facts):
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

    def execute(self, facts_set):
        # Create an empty context for when expressions to populate stuff with
        # Add all "facts" to this context. This will be used by accumulator and other DSL methods
        context = SimpleNamespace(_facts=facts_set, _changes = [], _rule = self.rule, _rules = self.rules, _global=self.global_ctx)

        all_cached = True
        # Evaluate all when clauses
        for i, when in enumerate(self.leaves):
            cached, result = when.execute(context, self.when_objs[i])
            logging.debug(f"Executed when expression for: {self}[{i}]: cached/result: {cached}:{result}")
            all_cached = all_cached and cached
            if not result:
                return None

        # If all the executions were cached, there is no need to execute the then
        if all_cached:
            return None
        
        # If we are here, it means all the when conditions were satisfied, execute the then expression
        logging.debug(f"Node: {self} with context:{context} all when clauses satisfied, going to execute the then clauses")
        for then in self.rule.thens:
            # Execute each function/lambda included in the rule
            then(context)

        result = {'insert': [], 'update': [], 'delete': []}
        # Report changes to the facts introduced by the execution of the above functions
        for change in context._changes:
            result[change[1]].append(change[0])
        logging.debug(f"Result from node: {self} execution, result: {result}")
        return result

    def __str__(self):
        return f"Node({self.id}, rule:{self.rule}, whens:{self.when_objs})"

    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
      return self.id == other.id