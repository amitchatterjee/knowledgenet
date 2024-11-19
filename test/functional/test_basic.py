import pytest
import sys
import os
import logging

from pyrete.rule import Rule,When
from pyrete.engine import Engine
from pyrete.dsl import assign

class C1:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return f"C1(val: {self.val})"
    def __repr__(self):
        return self.__str__()

class C2:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return f"C2(val: {self.val})"
    def __repr__(self):
        return self.__str__()


def test_rules_loading():
    rule_1 = Rule('test-rule-1',[
            When(C1, lambda facts: assign(facts, c1=facts.this) and facts.this.val > 1),
            When(C2, lambda facts: facts.this != facts.c1 and facts.c1.val > 1 and facts.this.val > 1)
        ],
        lambda facts: logging.debug("Large number"))
    engine = Engine([rule_1])
    facts = [C1(1), C1(2), C2(1), C2(2), C2(3)]
    engine.run(facts)