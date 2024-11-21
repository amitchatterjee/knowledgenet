import logging

from collections import deque

from pyrete.perms import permutations
from pyrete.graph import Node
from pyrete.utils import to_list

class Engine:
    def __init__(self, rules):
        # TODO add validations
        self.rules = rules

    def __insert(self, dq, node):
        # TODO check for dups - needed when inserting/updating facts from rules
        for i, item in enumerate(dq):
            if item.rule.rank > node.rule.rank:
                dq.insert(i,node)
                return
        dq.append(node)

    def run(self, facts):
        # Eliminate duplicates
        facts_set = set(facts)

        # Create a {class:[fact]}
        class_to_facts = {}
        for fact in facts_set:
            self.__add_to_class_facts_dict(class_to_facts, fact)

        self.create_dag(facts_set, class_to_facts)
        self.execute_dag(facts_set)
        return facts_set

    def execute_dag(self, facts_set):
        changes = False
        for node in self.dag:
            result = node.execute()
            if result:
                # If all conditions were satisfied and the thens were executed
                if len(result['insert']):
                    self.insert_to_dag(self.dag, facts_set, result['insert'])
                    # TODO change to True when the insert/update/delete logic is implemented
                    changes = False
            
                # TODO add update, delete handling
    
                if changes:
                    # If there were inserts updates or deletes, stop the current dag execution
                    break
        if changes:
            # re-execute the dag
            self.execute_dag(facts_set)

    def insert_to_dag(self, dag, facts_set, inserts):
        # TODO Lot more to happen here
        facts_set.update(inserts)
        
    def create_dag(self, facts_set, class_to_facts):
        self.dag = deque()
        for rule in self.rules:
            satisfies = True
            when_objs = []
            # For each class associated with the when clause, look if object(s) of that type exists. If objects exist for all of the when clauses, then this rule satisfies the need and is ready to be put in the DAG
            for when in to_list(rule.whens):
                if when.onclass not in class_to_facts:
                    satisfies = False
                    break
                when_objs.append(class_to_facts[when.onclass])

            if satisfies:
                # Get all the permutations associated with the objects
                perms = permutations(when_objs)                
                logging.debug(f"{rule}:perms: {perms}")
                # insert to the dag
                for e in perms:
                    logging.debug(f"Adding node: {rule}{e}")
                    self.__insert(self.dag, Node(rule, e, facts_set))
        logging.debug(f"Dag: {self.dag}")

    def __add_to_class_facts_dict(self, class_to_facts, fact):
        facts_list = class_to_facts[fact.__class__] if fact.__class__ in class_to_facts else []
        facts_list.append(fact)
        class_to_facts[fact.__class__] = facts_list