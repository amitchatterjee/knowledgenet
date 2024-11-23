class Factset:
    def __init__(self, facts):
        self.facts_set = set(self.fact)
        self.class_to_facts = {}
        self.__add_to_class_facts_dict(self.facts_set)

    def __add_to_class_facts_dict(self, fact):
        facts_list = self.class_to_facts[fact.__class__] if fact.__class__ in self.class_to_facts else []
        facts_list.append(fact)
        self.class_to_facts[fact.__class__] = facts_list