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
    
class P1:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return f"P1(val: {self.val})"
    def __repr__(self):
        return self.__str__()
    
class Ch1:
    def __init__(self, parent, val):
        self.parent = parent
        self.val = val
    def __str__(self):
        return f"Ch1(val: {self.val})"
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

def test_simple_rule_chanining():
    rule_1 = Rule('test_simple_rule_chaining_create_child',
                When(forClass(P1), expression(lambda ctx: ctx.this.val > 0)),
                Then(lambda ctx: insert(ctx, Ch1(ctx.this, 20))))
    rule_2 = Rule('test_simple_rule_chaining_child_linking',
                When(forClass(Ch1), expression(lambda ctx: ctx.this.val > 0)),
                Then(lambda ctx: insert(ctx, R1(ctx.this.parent, ctx.this))))
    engine = Engine([rule_1, rule_2])
    m1 = P1(20)
    facts = [m1]
    result_facts = engine.run(facts)
    results = []
    for fact in result_facts:
        if fact.__class__ == R1:
            results.append(fact)
    assert 1==len(results)
    assert 2 ==len(results[0].vals)
    assert m1 == results[0].vals[0]
    assert Ch1 == type(results[0].vals[1])

def test_rule_chanining_with_matching():
    rule_1 = Rule('test_simple_rule_chaining_with_matching',
                When(forClass(P1), expression(lambda ctx: ctx.this.val > 0)),
                Then(lambda ctx: insert(ctx, Ch1(ctx.this, 20))))
    rule_2 = Rule('test_simple_rule_chaining_child_matching', [
                    When(forClass(P1), expression(lambda ctx: ctx.this.val > 0 and assign(ctx,parent=ctx.this))),
                    When(forClass(Ch1), expression(lambda ctx: ctx.this.val > 0 and assign(ctx,child=ctx.this) and ctx.child.parent == ctx.parent))
                ],
                Then(lambda ctx: insert(ctx, R1(ctx.this.parent, ctx.child))))
    engine = Engine([rule_1, rule_2])
    m1 = P1(20)
    facts = [m1]
    result_facts = engine.run(facts)
    results = []
    for fact in result_facts:
        if fact.__class__ == R1:
            results.append(fact)
    assert 1==len(results)
    assert 2 ==len(results[0].vals)
    assert m1 == results[0].vals[0]
    assert Ch1 == type(results[0].vals[1])
