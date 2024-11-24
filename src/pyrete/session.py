import logging
from collections import deque

from pyrete.perms import permutations
from pyrete.graph import Node
from pyrete.factset import Factset

class Session:
    def __init__(self, ruleset, facts, globals=[]):
        self.ruleset = ruleset
        self.rules = ruleset.rules
        self.globals = globals
        self.factset = Factset()
        self.graph = deque()
        self.__add_facts(facts)

    def __str__(self):
        return f"Session(ruleset: {self.ruleset}, facts:{self.factset})"
    
    def __repr__(self):
        return self.__str__()

    def execute(self):
        self.__execute_graph()
        return self.factset.facts

    def __insert(self, node):
        # TODO check for dups - needed when inserting/updating facts from rules
        for i, each in enumerate(self.graph):
            if each.rule.rank > node.rule.rank:
                self.graph.insert(i, node)
                return
        self.graph.append(node)

    def __execute_graph(self, recursion_count = 0):
        logging.debug(f"Executing pass: {recursion_count}")
        counts = 0
        for node in self.graph:
            result = node.execute(self.factset)
            if result:
                # If all conditions were satisfied and the thens were executed
                if len(result['insert']):
                    new_facts = result['insert']
                    counts = counts + self.__add_facts(new_facts)
                    logging.debug(f"Inserted facts: {new_facts}")
            
                if len(result['update']):
                    updated_facts = result['update']
                    counts = counts + self.__update_facts(updated_facts)
                    logging.debug(f"Updated facts: {updated_facts}")

                if len(result['delete']):
                   deleted_facts = result['delete']
                   counts = counts + self.__delete_facts(deleted_facts)
                   logging.debug(f"Deleted facts: {deleted_facts}")

                if counts:
                    # If there were inserts updates or deletes, stop the current graph execution and re-execute the graph
                    self.__execute_graph(recursion_count + 1)
                    break
        logging.debug(f"Executed pass: {recursion_count}")        
    
    def __delete_facts(self, deleted_facts):
        to_delete = []
        for i, node in enumerate(self.graph):
            for obj in node.when_objs:
                if obj in deleted_facts:
                    to_delete.append(i)
                    break
        for index in reversed(to_delete):
            del self.graph[index]
        return len(to_delete)

    def __update_facts(self, updated_facts):
        count = 0
        for node in self.graph:
            count = count + node.invalidate_leaves(updated_facts)
        return count

    def __add_facts(self, new_facts):
        # The new_facts variable contains a (deduped) set
        new_facts = self.factset.add_facts(new_facts)

        logging.debug(f"Adding to graph: all facts: {self.factset.facts}, new: {new_facts}")
        node_count = 0
        for rule in self.rules:
            satisfies = True
            when_objs = []
            # For each class associated with the when clause, look if object(s) of that type exists. If objects exist for all of the when clauses, then this rule satisfies the need and is ready to be put in the graph
            for when in rule.whens:
                objs = self.factset.facts_of_type(when.onclass)
                if not objs:
                    satisfies = False
                    break
                when_objs.append(objs)

            if satisfies:
                # Get all the permutations associated with the objects
                perms = permutations(when_objs, new_facts)                
                logging.debug(f"{rule}, object permuation: {perms}")
                # insert to the graph
                for e in perms:
                    node = Node(rule, self.rules, self.globals, e)
                    logging.debug(f"Adding node: {node}")
                    self.__insert(node)
                    node_count = node_count+1
        logging.debug(f"Updated graph: {self.graph}, graph size: {len(self.graph)}, new nodes count: {node_count}")
        return node_count