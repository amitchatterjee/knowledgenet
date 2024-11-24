import logging

from pyrete.rule import Rule,When
from pyrete.ruleset import Ruleset
from pyrete.service import Service
from pyrete.dsl import forType, expression, Then
from pyrete.helper import assign
from pyrete.signal import insert, update, delete

from util import find_result_of_type
from fact_type import C1, C2, R1, P1, Ch1

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