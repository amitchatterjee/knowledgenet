import logging

from pyrete.rule import Rule,When
from pyrete.ruleset import Ruleset
from pyrete.service import Service
from pyrete.dsl import forType, expression, Then
from pyrete.helper import assign
from pyrete.signal import insert

from util import find_result_of_type
from fact_type import C1, C2, R1, P1, Ch1

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