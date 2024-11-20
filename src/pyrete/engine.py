import logging

from collections import deque

from pyrete.perms import permutations
from pyrete.dag_node import DagNode


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
        facts_space = set(facts)

        # Create a {class:[fact]}
        class_to_facts = {}
        for fact in facts_space:
            facts_list = class_to_facts[fact.__class__] if fact.__class__ in class_to_facts else []
            facts_list.append(fact)
            class_to_facts[fact.__class__] = facts_list

        dag = deque()
        for rule in self.rules:
            satisfies = True
            when_objs = []
            # For each class associated with the when clause, look if object(s) of that type exists. If objects exist for all of the when clauses, then this rule satisfies the need and is ready to be put in the DAG
            for when in rule.whens:
                if when.clazz not in class_to_facts:
                    satisfies = False
                    break
                when_objs.append(class_to_facts[when.clazz])
            if satisfies:
                logging.debug(f"{rule}:satisifes. facts: {when_objs}")
                # Get all the permutations associated with the objects
                perms = permutations(when_objs)                
                logging.debug(f"{rule}:perms: {perms}")
                # insert to the dag
                for e in perms:
                    self.__insert(dag, DagNode(rule, e, facts))
                logging.debug(dag)
            
            for node in dag:
                node.execute()
        
        # Get combinations

        # TODO evaluate expressions

        return facts_space