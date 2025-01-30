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
        rules_list.sort(key=lambda rule: rule.order)
        self.rules = to_tuple(rules_list)
 
    def __str__(self):
        return f"Ruleset({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name