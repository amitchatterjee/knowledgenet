from rule import Rule
from util import to_tuple
from typing import Union
class Ruleset:
    def __init__(self, id:str, rules:Union[Rule,tuple[Rule],list[Rule]], global_ctx={}):
        self.id = id
        # TODO add rule validations
        # TODO add rule sequencing
        self.rules = to_tuple(rules)
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
