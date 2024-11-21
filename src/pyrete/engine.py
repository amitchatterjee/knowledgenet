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
                logging.debug(f"{rule}:satisifes. facts: {when_objs}")
                # Get all the permutations associated with the objects
                perms = permutations(when_objs)                
                logging.debug(f"{rule}:perms: {perms}")
                # insert to the dag
                for e in perms:
                    self.__insert(self.dag, Node(rule, e, facts_set))
                logging.debug(self.dag)
            
        for node in self.dag:
            result = node.execute()
            if result:
                # If all conditions were satisfied and the thens were executed
                # TODO Lot more to happen here
                for insert in result['insert']:
                    facts_set.add(insert)
        return facts_set

    def __add_to_class_facts_dict(self, class_to_facts, fact):
        facts_list = class_to_facts[fact.__class__] if fact.__class__ in class_to_facts else []
        facts_list.append(fact)
        class_to_facts[fact.__class__] = facts_list