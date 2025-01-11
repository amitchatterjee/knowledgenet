import logging
from typing import Union

from knowledgenet.util import to_list, to_tuple
from knowledgenet.rule import Rule

class Ruleset:
    def __init__(self, id:str, rules:Union[Rule,tuple[Rule],list[Rule]], global_ctx={}):
        self.id = id
        self._order_rules(rules)
        self.global_ctx = global_ctx
        logging.debug("%s - added %d rules", self, len(self.rules))

    def _order_rules(self, rules):
        rules_list = to_list(rules)
        # TODO only rule.order based ordering is implemented for now, add other stuff including:
        # - merge hints
        # - collection goes after the types it collects
        # - etc.
        rules_list.sort(key=lambda rule: rule.order)
        for i, rule in enumerate(rules_list):
            rule.ordinal = i
        self.rules = to_tuple(rules_list)
 
    def __str__(self):
        return f"Ruleset({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
    
    def comparator(self, obj, other):
        return obj.rule.ordinal - other.rule.ordinal
