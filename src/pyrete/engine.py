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

        dag = deque()
        self.update_dag(dag, [], class_to_facts)
        self.execute_dag(dag, facts_set, class_to_facts)
        return facts_set

    def execute_dag(self, dag, facts_set, class_to_facts):
        changes = False
        for node in dag:
            result = node.execute(facts_set)
            if result:
                # If all conditions were satisfied and the thens were executed
                if len(result['insert']):
                    facts_set.update(result['insert'])
                    for insert in result['insert']:
                        self.__add_to_class_facts_dict(class_to_facts, insert)
                    logging.debug(f"Inserted facts: {result['insert']}")
                    count = self.update_dag(dag, result['insert'], class_to_facts)
                    if count:
                        changes = True
            
                # TODO add update, delete handling

                if changes:
                    # If there were inserts updates or deletes, stop the current dag execution
                    break
        if changes:
            # re-execute the dag
            self.execute_dag(dag, facts_set, class_to_facts)
        
        
    def update_dag(self, dag, include_only, class_to_facts):
        node_count = 0
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
                perms = permutations(when_objs, include_only)                
                logging.debug(f"{rule}:perms: {perms}")
                # insert to the dag
                for e in perms:
                    logging.debug(f"Adding node: {rule}{e}")
                    self.__insert(dag, Node(rule, e))
                    node_count = node_count+1
        logging.debug(f"Dag: {dag}")
        return node_count

    def __add_to_class_facts_dict(self, class_to_facts, fact):
        facts_list = class_to_facts[fact.__class__] if fact.__class__ in class_to_facts else []
        facts_list.append(fact)
        class_to_facts[fact.__class__] = facts_list