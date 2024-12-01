from typing import get_origin, get_args
class Factset:
    def __init__(self):
        self.facts = set()
        self.__class_to_facts = {}

    def __str__(self):
        return f"Factset({self.facts})"
    
    def __repr__(self):
        return self.__str__()

    def add_facts(self, f):
        diff = set(f) - self.facts
        self.facts.update(diff)
        for fact in diff:
            self.__add_to_class_facts_dict(fact)
        return diff

    def __add_to_class_facts_dict(self, fact):
        facts_list = self.__class_to_facts[type(fact)] if type(fact) in self.__class_to_facts else []
        facts_list.append(fact)
        self.__class_to_facts[type(fact)] = facts_list

    def facts_of_type(self, cls):
        #print(f"origin:{get_origin(cls)}, args: {get_args(cls)}")
        return self.__class_to_facts[cls] if cls in self.__class_to_facts else None
