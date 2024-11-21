import pytest
import sys
import os
import logging

from pyrete.rule import Rule,When
from pyrete.engine import Engine
from pyrete.dsl import assign, insert, forClass, expression, Then

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

def test_one_rule_single_when_then():
    rule = Rule('test_one_rule_single_when_then', 
                When(forClass(C1), expression(lambda ctx: assign(ctx, c1=ctx.this) and ctx.this.val > 1)),
                Then(lambda ctx: insert(ctx, R1(ctx.c1,None))))

    engine = Engine([rule])
    m1 = C1(2)
    facts = [C1(1), m1]
    result_facts = engine.run(facts)
    results = []
    for fact in result_facts:
        if fact.__class__ == R1:
            results.append(fact)
    assert 1==len(results)
    assert 2 ==len(results[0].vals)
    assert (m1,None) == results[0].vals

def test_one_rule_multiple_when_thens():
    rule = Rule('test_one_rule_multiple_when_thens', [
                When(forClass(C1), expression(lambda ctx: assign(ctx, c1=ctx.this) and ctx.this.val > 1)),
                When(forClass(C2), expression(lambda ctx: assign(ctx, c2=ctx.this) and ctx.this.val != ctx.c1.val and ctx.this.val > 1))
                ],
                Then([
                    lambda ctx: logging.info(f"Found match: {(ctx.c1,ctx.c2)}"),
                    lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2))]))

    engine = Engine([rule])
    m1 = C1(2)
    m2 = C2(3)
    facts = [C1(1), m1, C2(1), C2(2), m2]
    result_facts = engine.run(facts)
    results = []
    for fact in result_facts:
        if fact.__class__ == R1:
            results.append(fact)
    assert 1==len(results)
    assert 2 ==len(results[0].vals)
    assert (m1,m2) == results[0].vals
    
