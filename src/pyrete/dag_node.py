from types import SimpleNamespace
import logging

class WhenLeaf:
    def __init__(self, rule, when_index, all_facts):
        self.rule = rule
        self.when_index = when_index
        self.all_facts = all_facts
        self.executed = False

    def execute(self, context):
        if self.executed:
            # Return the previous result
            return self.result
        # Else, evaluate the expression
        self.result = self.rule.whens[self.when_index].exp(context)
        self.executed = True
        return self.result

class DagNode:
    def __init__(self, rule, when_objs, all_facts):
        self.rule = rule
        self.when_objs = when_objs

        # Create an empty context for when expressions to populate stuff with
        # Add all "facts" to this context. This will be used by accumulator and other DSL methods
        self.context = SimpleNamespace(facts=all_facts)

        # Create when expression execution context
        self.when_executions = []
        for i, when in enumerate(rule.whens):
            self.when_executions.append(WhenLeaf(rule, i, all_facts))

    def execute(self):
        # Evaluate all when clauses
        for i, when in enumerate(self.when_executions):
            # Add a "this" to the context
            self.context.this = self.when_objs[i]

            result = when.execute(self.context)
            logging.debug(f"Executed exp: {self.rule}[{i}]: {result}")
            if not result:
                return
        # If we are here, it means all the when conditions were satisfied, execute the then expression
        logging.debug(f"Rule: {self.rule} with context:{self.context} when clauses satisfied, going to execute the then clause")
        self.rule.then(self.context)

    def __str__(self):
        return f"DagNode(rule:{self.rule}, whens:{self.when_objs})"

    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        if self.rule != other.rule:
            return False
        if len(self.when_objs) != len(other.when_objs):
            return False
        for i, when_obj in enumerate(self.when_objs):
            if when_obj != other.when_objs[i]:
                return False
        return True