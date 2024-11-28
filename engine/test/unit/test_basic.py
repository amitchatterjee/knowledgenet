import logging

from rule import Rule,Condition
from ruleset import Ruleset
from knowledge import Knowledge
from helper import assign
from notify import insert
from service import execute

from test_helpers.test_util import find_result_of_type
from test_helpers.test_facts import C1, C2, R1, P1, Ch1

def test_one_rule_single_when_then():
    rule = Rule(id='r1',
                when=Condition(for_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    result_facts = execute(Knowledge('k1', [Ruleset('rs1', [rule])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert facts[1] == matching[0].vals[0]

def test_one_rule_multiple_when_thens():
    rule = Rule(id='r1', when=[
                Condition(for_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                Condition(for_type=C2, matches_exp=lambda ctx, this: assign(ctx, c2=this) and this.val != ctx.c1.val and this.val > 1)],
                then=[
                    lambda ctx: logging.info(f"Found match: {(ctx.c1,ctx.c2)}"),
                    lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2))])

    facts = [C1(1), C1(2), C2(1), C2(2), C2(3)]
    result_facts = execute(Knowledge('k1', [Ruleset('rs1', [rule])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert (facts[1],facts[4]) == matching[0].vals