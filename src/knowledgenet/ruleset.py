"""Ruleset model for grouping related rules into an execution phase."""

import logging

from knowledgenet.util import to_list, to_tuple
from knowledgenet.rule import Rule

class Ruleset:
    """Groups related rules under one identifier.

    Rules are normalized and sorted by ``rule.order`` before runtime execution
    to produce deterministic graph insertion order.
    """

    def __init__(self, id:str, rules:Rule|tuple[Rule]|list[Rule], global_ctx: dict[str, object] | None = None) -> None:
        if global_ctx is None:
            global_ctx = {}
        self.id = id
        self._order_rules(rules)
        self.global_ctx = global_ctx
        logging.debug("%s - added %d rules", self, len(self.rules))

    def _order_rules(self, rules: Rule|tuple[Rule]|list[Rule]) -> None:
        rules_list = to_list(rules)
        rules_list.sort(key=lambda rule: rule.order)
        self.rules = to_tuple(rules_list)

    def __str__(self) -> str:
        return f"Ruleset({self.id})"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ruleset):
            return NotImplemented
        return self.id == other.id