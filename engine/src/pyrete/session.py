import logging
import uuid
from collections import deque

from perm import combinations
from node import Node
from factset import Factset
from graph import Graph

class Session:
    def __init__(self, ruleset, facts, id=uuid.uuid1(), global_ctx={}):
        self.id = id
        self.ruleset = ruleset
        self.rules = ruleset.rules
        self.global_ctx = global_ctx
        self.factset = Factset()
        self.graph = Graph(self.__comparator)
        self.__add_facts(facts)

    def __str__(self):
        return f"Session({self.id}, ruleset: {self.ruleset}, facts:{self.factset})"
    
    def __repr__(self):
        return self.__str__()

    def execute(self):
        self.__execute_graph()
        return self.factset.facts

    def __comparator(self, obj, other):
        # TODO only rule.order based ordering is implemented for now
        return obj.rule.order - other.rule.order


    def __execute_graph(self):
        logging.debug(f"Executing rules on graph")
        self.graph.new_cursor()
        while True:
            node = self.graph.next()
            if node is None:
                # Reached the end of the graph
                break

            # Execute the rule on the node
            result = node.execute(self.factset)
            counts = 0
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
                    # if there were inserts/updates/deletes
                    # TODO start from the beginning again. This need to change to start from the leftmost node where a change occured
                    self.graph.new_cursor()
    
    def __delete_facts(self, deleted_facts):
        cursor_name = 'delete'
        self.graph.new_cursor(cursor_name=cursor_name)
        deduped_deletes = set(deleted_facts)
        counts = 0
        while True:
            element = self.graph.next_element(cursor_name)
            if element is None:
                break
            print(element.obj)
            if len([value for value in element.obj.when_objs if value in deduped_deletes]):
                self.graph.delete_element(element)
                counts = counts+1
        return counts

    def __update_facts(self, updated_facts):
        cursor_name = 'update'
        self.graph.new_cursor(cursor_name=cursor_name)
        deduped_updates = set(updated_facts)
        counts = 0
        while True:
            node = self.graph.next(cursor_name)
            if node is None:
                break
            counts = counts + 1 if node.invalidate_leaves(deduped_updates) else 0
        return counts

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
                objs = self.factset.facts_of_type(when.for_type)
                if not objs:
                    satisfies = False
                    break
                when_objs.append(objs)

            if satisfies:
                # Get all the permutations associated with the objects
                perms = combinations(when_objs, new_facts)                
                logging.debug(f"{rule}, object permuation: {perms}")
                # insert to the graph
                for each in perms:
                    node = Node(int(uuid.uuid4().int), rule, self.rules, self.global_ctx, each)
                    logging.debug(f"Adding node: {node}")
                    self.graph.add(node)
                    node_count = node_count+1
        logging.debug(f"Updated graph: {self.graph}, new nodes count: {node_count}")
        return node_count