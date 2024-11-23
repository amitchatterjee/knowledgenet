import pytest
import sys
import os
import logging

from pyrete.rule import Rule,When
from pyrete.ruleset import Ruleset
from pyrete.dsl import assign, insert, update, forClass, expression, Then

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

def find_result_of_type(cls, results):
    return [result for result in results if result.__class__ == cls]

def test_one_rule_single_when_then():
    rule = Rule('r1', 
                When(forClass(C1), expression(lambda ctx: assign(ctx, c1=ctx.this) and ctx.this.val > 1)),
                Then(lambda ctx: insert(ctx, R1(ctx.c1))))

    ruleset = Ruleset('rs1', [rule])
    m1 = C1(2)
    facts = [C1(1), m1]
    result_facts = ruleset.run(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert m1 == matching[0].vals[0]

def test_one_rule_multiple_when_thens():
    rule = Rule('r1', [
                When(forClass(C1), expression(lambda ctx: assign(ctx, c1=ctx.this) and ctx.this.val > 1)),
                When(forClass(C2), expression(lambda ctx: assign(ctx, c2=ctx.this) and ctx.this.val != ctx.c1.val and ctx.this.val > 1))
                ],
                Then([
                    lambda ctx: logging.info(f"Found match: {(ctx.c1,ctx.c2)}"),
                    lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2))]))

    ruleset = Ruleset('rs1', [rule])
    m1 = C1(2)
    m2 = C2(3)
    facts = [C1(1), m1, C2(1), C2(2), m2]
    result_facts = ruleset.run(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert (m1,m2) == matching[0].vals

def test_simple_rule_chanining_with_insert():
    rule_1 = Rule('r1',
                When(forClass(P1), expression(lambda ctx: ctx.this.val > 0)),
                Then(lambda ctx: insert(ctx, Ch1(ctx.this, 20))))
    rule_2 = Rule('r2',
                When(forClass(Ch1), expression(lambda ctx: ctx.this.val > 0)),
                Then(lambda ctx: insert(ctx, R1(ctx.this.parent, ctx.this))))
    
    ruleset = Ruleset('rs1', [rule_1, rule_2])
    m1 = P1(20)
    facts = [m1]
    result_facts = ruleset.run(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert m1 == matching[0].vals[0]
    assert Ch1 == type(matching[0].vals[1])

def test_rule_chanining_with_insert_and_matching():
    rule_1 = Rule('r1',
                When(forClass(P1), expression(lambda ctx: ctx.this.val > 0)),
                Then(lambda ctx: insert(ctx, Ch1(ctx.this, 20))))
    rule_2 = Rule('r2', [
                    When(forClass(P1), expression(lambda ctx: ctx.this.val > 0 and assign(ctx,parent=ctx.this))),
                    When(forClass(Ch1), expression(lambda ctx: ctx.this.val > 0 and assign(ctx,child=ctx.this) and ctx.child.parent == ctx.parent))
                ],
                Then(lambda ctx: insert(ctx, R1(ctx.this.parent, ctx.child))))
    ruleset = Ruleset('rs1', [rule_1, rule_2])
    m1 = P1(20)
    facts = [m1]
    result_facts = ruleset.run(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert m1 == matching[0].vals[0]
    assert Ch1 == type(matching[0].vals[1])

def test_simple_rule_chanining_with_update():
    def zero_out(ctx):
        ctx.c1.val = 0
        update(ctx, ctx.c1)
    rule_1 = Rule('r1',
                When(forClass(C1), expression(lambda ctx: ctx.this.val > 0 and assign(ctx, c1=ctx.this))),
                Then(zero_out))
    rule_2 = Rule('r2',
                When(forClass(C1), expression(lambda ctx: ctx.this.val <= 0 and assign(ctx, c2=ctx.this))),
                Then(lambda ctx: insert(ctx, R1(ctx.c2))))
    
    ruleset = Ruleset('rs1', [rule_1, rule_2])
    m1 = C1(20)
    facts = [m1]
    result_facts = ruleset.run(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 1 ==len(matching[0].vals)
    assert m1 == matching[0].vals[0]