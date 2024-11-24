import logging

from pyrete.rule import Rule,When
from pyrete.ruleset import Ruleset
from pyrete.service import Service
from pyrete.dsl import assign, forType, expression, Then
from pyrete.signal import insert, update, delete

from util import find_result_of_type

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
    rule = Rule('r1', 
                When(forType(C1), expression(lambda ctx, this: assign(ctx, c1=this) and this.val > 1)),
                Then(lambda ctx: insert(ctx, R1(ctx.c1))))
    facts = [C1(1), C1(2)]
    result_facts = Service('ts1', [Ruleset('rs1', [rule])]).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert facts[1] == matching[0].vals[0]

def test_one_rule_multiple_when_thens():
    rule = Rule('r1', [
                When(forType(C1), expression(lambda ctx, this: assign(ctx, c1=this) and this.val > 1)),
                When(forType(C2), expression(lambda ctx, this: assign(ctx, c2=this) and this.val != ctx.c1.val and this.val > 1))
                ],
                Then([
                    lambda ctx: logging.info(f"Found match: {(ctx.c1,ctx.c2)}"),
                    lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2))]))

    facts = [C1(1), C1(2), C2(1), C2(2), C2(3)]
    result_facts = Service('ts1', [Ruleset('rs1', [rule])]).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert (facts[1],facts[4]) == matching[0].vals

def test_simple_rule_chanining_with_insert():
    rule_1 = Rule('r1',
                When(forType(P1), expression(lambda ctx, this: this.val > 0 and assign(ctx, parent=this))),
                Then(lambda ctx: insert(ctx, Ch1(ctx.parent, 20))))
    rule_2 = Rule('r2',
                When(forType(Ch1), expression(lambda ctx, this: this.val > 0 and assign(ctx, child=this))),
                Then(lambda ctx: insert(ctx, R1(ctx.child.parent, ctx.child))))
    
    facts = [P1(20)]
    result_facts = Service('ts1', [Ruleset('rs1', [rule_1, rule_2])]).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]
    assert Ch1 == type(matching[0].vals[1])

def test_rule_chanining_with_insert_and_matching():
    rule_1 = Rule('r1',
                When(forType(P1), expression(lambda ctx, this: this.val > 0 and assign(ctx, parent=this))),
                Then(lambda ctx: insert(ctx, Ch1(ctx.parent, 20))))
    rule_2 = Rule('r2', [
                    When(forType(P1), expression(lambda ctx, this: this.val > 0 and assign(ctx,parent=this))),
                    When(forType(Ch1), expression(lambda ctx, this: this.val > 0 and assign(ctx,child=this) and ctx.child.parent == ctx.parent))
                ],
                Then(lambda ctx: insert(ctx, R1(ctx.parent, ctx.child))))
    facts = [P1(20)]
    result_facts = Service('ts1', [Ruleset('rs1', [rule_1, rule_2])]).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]
    assert Ch1 == type(matching[0].vals[1])

def test_simple_rule_chanining_with_update():
    def zero_out(ctx):
        ctx.c1.val = 0
        update(ctx, ctx.c1)
    rule_1 = Rule('r1',
                When(forType(C1), expression(lambda ctx, this: this.val > 0 and assign(ctx, c1=this))),
                Then(zero_out))
    rule_2 = Rule('r2',
                When(forType(C1), expression(lambda ctx, this: this.val <= 0 and assign(ctx, c2=this))),
                Then(lambda ctx: insert(ctx, R1(ctx.c2))))    
    facts = [C1(20)]
    result_facts = Service('ts1', [Ruleset('rs1', [rule_1, rule_2])]).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 1 ==len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]

def test_rule_chanining_with_delete_and_matching():
    rule_1 = Rule('r1',
                When(forType(P1), expression(lambda ctx, this: this.val > 0 and assign(ctx, parent=this))),
                Then(lambda ctx: delete(ctx, ctx.parent)))
    rule_2 = Rule('r2', [
                    When(forType(P1), expression(lambda ctx, this: this.val > 0 and assign(ctx,parent=this))),
                    When(forType(Ch1), expression(lambda ctx, this: this.val > 0 and assign(ctx,child=this) and this.parent == ctx.parent))
                ],
                Then(lambda ctx: insert(ctx, R1(ctx.parent, ctx.child))), rank=1)
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = Service('ts1', [Ruleset('rs1', [rule_1, rule_2])]).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 0 == len(matching)