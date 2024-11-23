class Factset:
    def __init__(self):
        self.facts_set = set()
        self.class_to_facts = {}

    def __str__(self):
        return f"Factset({self.facts_set})"
    
    def __repr__(self):
        return self.__str__()

    def add_facts(self, facts):
        diff = set(facts) - self.facts_set
        self.facts_set.update(diff)
        for fact in diff:
            self.__add_to_class_facts_dict(fact)
        return diff

    def __add_to_class_facts_dict(self, fact):
        facts_list = self.class_to_facts[fact.__class__] if fact.__class__ in self.class_to_facts else []
        facts_list.append(fact)
        self.class_to_facts[fact.__class__] = facts_list