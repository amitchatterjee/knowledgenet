import pytest
import logging

from rule import Rule,Condition
from ruleset import Ruleset
from repository import Repository
from helper import assign
from controls import insert
from service import execute

from ftypes import Collector

from test_helpers.test_util import find_result_of_type
from test_helpers.test_facts import C1, C2, R1, P1, Ch1

def test_collector_in_input_facts():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=Collector, id='sum_of_c1s', matches_exp=lambda ctx, this: this.sum > 10 and assign(ctx, sum=this.sum, size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(10), Collector(of_type=C1, id='sum_of_c1s', nvalue=lambda obj: obj.val)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 20 == matching[0].vals[0]
    assert 2 == matching[0].vals[1]

def test_collector_fact_insertion():
    rule_1 = Rule(id='r1', order=0,
                  when=Condition(of_type=C1, matches_exp=lambda ctx, this: this.val > 10),
                  then=lambda ctx: insert(ctx, C1(1)))
    rule_2 = Rule(id='r2',
                when=Condition(of_type=Collector, id='sum_of_c1s', matches_exp=lambda ctx, this: this.sum > 10 and assign(ctx, sum=this.sum, size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, id='sum_of_c1s', nvalue=lambda obj: obj.val)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 31 == matching[0].vals[0]
    assert 3 == matching[0].vals[1]
    # TODO this is not working. Change the order to 1 in rule_1