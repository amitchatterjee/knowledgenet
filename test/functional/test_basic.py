import pytest
import sys
import os
import logging

from pyrete.rule import Rule,When
from pyrete.engine import Engine
from pyrete.dsl import assign, insert

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
    
class R1:
    def __init__(self, *vals):
        self.vals = vals
    def __str__(self):
        return f"R1(vals: {self.vals})"
    def __repr__(self):
        return self.__str__()
    
def test_one_rule_execution():
    rule_1 = Rule('test-rule-1',[
            When(C1, lambda ctx: assign(ctx, c1=ctx.this) and ctx.this.val > 1),
            When(C2, lambda ctx: assign(ctx, c2=ctx.this) and ctx.this.val != ctx.c1.val and ctx.this.val > 1)
        ],
        lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2)))
    engine = Engine([rule_1])
    m1 = C1(2)
    m2 = C2(3)
    facts = [C1(1), m1, C2(1), C2(2), m2]
    engine.run(facts)
    results = []
    for fact in facts:
        if fact.__class__ == R1:
            results.append(fact)
    assert 1==len(results)
    assert 2 ==len(results[0].vals)
    assert (m1,m2) == results[0].vals
    
