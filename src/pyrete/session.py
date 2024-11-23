import logging
from collections import deque

from pyrete.perms import permutations
from pyrete.graph import Node
from pyrete.utils import to_list
from pyrete.factset import Factset

class Session:
    def __init__(self, ruleset, globals=[]):
        self.ruleset = ruleset
        self.rules = ruleset.rules
        self.globals = globals
        self.factset = Factset()
        self.dag = deque()

    def run(self, facts):
        self.__add_to_dag(facts)
        self.__execute_dag()
        return self.factset.facts_set

    def __insert(self, node):
        # TODO check for dups - needed when inserting/updating facts from rules
        for i, each in enumerate(self.dag):
            if each.rule.rank > node.rule.rank:
                self.dag.insert(i, node)
                return
        self.dag.append(node)

    def __execute_dag(self, recursion_count = 0):
        logging.debug(f"Executing pass: {recursion_count}")
        counts = 0
        for node in self.dag:
            result = node.execute(self.factset.facts_set)
            if result:
                # If all conditions were satisfied and the thens were executed
                if len(result['insert']):
                    new_facts = result['insert']
                    counts = counts + self.__add_to_dag(new_facts)
                    logging.debug(f"Inserted facts: {new_facts}")
            
                if len(result['update']):
                    updated_facts = result['update']
                    counts = counts + self.__update_dag(updated_facts)
                    logging.debug(f"Updated facts: {updated_facts}")

                if len(result['delete']):
                   deleted_facts = result['delete']
                   counts = counts + self.__delete_nodes(deleted_facts)
                   logging.debug(f"Deleted facts: {deleted_facts}")

                if counts:
                    # If there were inserts updates or deletes, stop the current dag execution and re-execute the dag
                    self.__execute_dag(recursion_count + 1)
                    break
        logging.debug(f"Executed pass: {recursion_count}")        
    
    def __delete_nodes(self, deleted_facts):
        to_delete = []
        for i, node in enumerate(self.dag):
            for obj in node.when_objs:
                if obj in deleted_facts:
                    to_delete.append(i)
                    break
        for index in reversed(to_delete):
            del self.dag[index]
        return len(to_delete)

    def __update_dag(self, updated_facts):
        count = 0
        for node in self.dag:
            count = count + node.invalidate_leaves(updated_facts)
        return count

    def __add_to_dag(self, new_facts):
        # The new_facts variable contains a (deduped) set
        new_facts = self.factset.add_facts(new_facts)

        logging.debug(f"Adding to dag: all facts: {self.factset.class_to_facts.values()}, new: {new_facts}")
        node_count = 0
        for rule in self.rules:
            satisfies = True
            when_objs = []
            # For each class associated with the when clause, look if object(s) of that type exists. If objects exist for all of the when clauses, then this rule satisfies the need and is ready to be put in the DAG
            for when in to_list(rule.whens):
                if when.onclass not in self.factset.class_to_facts:
                    satisfies = False
                    break
                when_objs.append(self.factset.class_to_facts[when.onclass])

            if satisfies:
                # Get all the permutations associated with the objects
                perms = permutations(when_objs, new_facts)                
                logging.debug(f"{rule}, object permuation: {perms}")
                # insert to the dag
                for e in perms:
                    node = Node(rule, self.rules, self.globals, e)
                    logging.debug(f"Adding node: {node}")
                    self.__insert(node)
                    node_count = node_count+1
        logging.debug(f"Updated dag: {self.dag}, dag size: {len(self.dag)}, new nodes count: {node_count}")
        return node_count