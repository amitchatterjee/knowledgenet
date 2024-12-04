import pytest
import logging

from rule import Rule,Condition
from ruleset import Ruleset
from repository import Repository
from helper import assign
from notify import insert
from service import execute
from typing import Tuple

from test_helpers.test_util import find_result_of_type
from test_helpers.test_facts import C1, C2, R1, P1, Ch1

def test_one_rule_single_when_then():
    rule = Rule(id='r1',
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    result_facts = execute(Repository('m1', [Ruleset('rs1', [rule])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert facts[1] == matching[0].vals[0]

def test_one_rule_multiple_when_thens():
    rule = Rule(id='r1', when=[
                Condition(of_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                Condition(of_type=C2, matches_exp=lambda ctx, this: assign(ctx, c2=this) and this.val != ctx.c1.val and this.val > 1)],
                then=[
                    lambda ctx: logging.info(f"Found match: {(ctx.c1,ctx.c2)}"),
                    lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2))])

    facts = [C1(1), C1(2), C2(1), C2(2), C2(3)]
    result_facts = execute(Repository('m1', [Ruleset('rs1', [rule])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert (facts[1],facts[4]) == matching[0].vals

def test_condition_with_container_objs():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=tuple, matches_exp=lambda ctx, this: assign(ctx, l=this) and len(this) >= 2),
                then=lambda ctx: insert(ctx, R1(ctx.l)))
    rule_2 = Rule(id='r2',
                when=Condition(of_type=frozenset, matches_exp=lambda ctx, this: assign(ctx, d=this) and 'name' in this),
                then=lambda ctx: insert(ctx, R1(ctx.d)))
    facts = [(C1(1), C1(2)), frozenset({'name': 'tester'})]
    result_facts = execute(Repository('m1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    matching.sort(key=lambda o: str(o)) # Sort to make the order predictable
    assert 2== len(matching)
    assert 1 == len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]
    assert 1 == len(matching[1].vals)
    assert facts[1] == matching[1].vals[0]