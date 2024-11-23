import logging
from collections import deque

from pyrete.perms import permutations
from pyrete.graph import Node
from pyrete.utils import to_list

class Session:
    def __init__(self, rules):
        self.rules = rules

         # Create an empty facts_set that contains all facts
        self.facts_set = set()

        # Create a dictionary: {class:[fact]}
        self.class_to_facts = {}

        self.dag = deque()

    def run(self, facts):
        self.__add_to_dag(facts)
        self.__execute_dag()
        return self.facts_set

    def __insert(self, node):
        # TODO check for dups - needed when inserting/updating facts from rules
        for i, item in enumerate(self.dag):
            if item.rule.rank > node.rule.rank:
                self.dag.insert(i, node)
                return
        self.dag.append(node)

    def __execute_dag(self, recursion_count = 0):
        logging.debug(f"Executing pass: {recursion_count}")
        counts = 0
        for node in self.dag:
            result = node.execute(self.facts_set)
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

                # TODO add delete handling

                if counts:
                    # If there were inserts updates or deletes, stop the current dag execution and re-execute the dag
                    self.__execute_dag(recursion_count + 1)
                    break
        logging.debug(f"Executed pass: {recursion_count}")        
    
    def __update_dag(self, updated_facts):
        count = 0
        for node in self.dag:
            count = count + node.invalidate_leaves(updated_facts)
        return count

    def __add_to_dag(self, new_facts):
        self.facts_set.update(new_facts)
        for fact in new_facts:
            self.__add_to_class_facts_dict(fact)

        logging.debug(f"Adding to dag: all facts: {self.class_to_facts.values()}, new: {new_facts}")
        node_count = 0
        for rule in self.rules:
            satisfies = True
            when_objs = []
            # For each class associated with the when clause, look if object(s) of that type exists. If objects exist for all of the when clauses, then this rule satisfies the need and is ready to be put in the DAG
            for when in to_list(rule.whens):
                if when.onclass not in self.class_to_facts:
                    satisfies = False
                    break
                when_objs.append(self.class_to_facts[when.onclass])

            if satisfies:
                # Get all the permutations associated with the objects
                perms = permutations(when_objs, new_facts)                
                logging.debug(f"{rule}, object permuation: {perms}")
                # insert to the dag
                for e in perms:
                    logging.debug(f"Adding node: {rule}{e}")
                    self.__insert(Node(rule, e))
                    node_count = node_count+1
        logging.debug(f"Updated dag: {self.dag}, new nodes count: {node_count}")
        return node_count

    def __add_to_class_facts_dict(self, fact):
        facts_list = self.class_to_facts[fact.__class__] if fact.__class__ in self.class_to_facts else []
        facts_list.append(fact)
        self.class_to_facts[fact.__class__] = facts_list