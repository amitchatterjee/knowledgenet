from rule import Rule

class Ruleset:
    def __init__(self, id:str, rules:list[Rule], global_ctx={}):
        self.id = id
        # TODO add rule validations
        self.rules = rules
        self.global_ctx = global_ctx

    def __str__(self):
        return f"Ruleset({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
    
    def comparator(self, obj, other):
        # TODO only rule.order based ordering is implemented for now
        return obj.rule.order - other.rule.order
