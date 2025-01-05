import sys
from collections import OrderedDict

from knowledgenet.rule import Collection, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert, delete, update
from knowledgenet.service import Service
from knowledgenet.collector import Collector

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1, P1, Ch1

def test_collector_syntax():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 10),
                  then=lambda ctx: insert(ctx, C1(1)))
    rule_2 = Rule(id='r2', order=1,
                when=Collection(group='sum_of_c1s', matches=lambda ctx, this: this.sum() > 10 and assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 31 == matching[0].vals[0]
    assert 3 == matching[0].vals[1]

def test_multiple_matches_syntax():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 10),
                  then=lambda ctx: insert(ctx, C1(1)))
    rule_2 = Rule(id='r2', order=1,
                when=Collection(group='sum_of_c1s', 
                        matches=[lambda ctx,this: this.sum() > 10, 
                                 lambda ctx,this: assign(ctx, sum=this.sum(), size=len(this.collection))]),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 31 == matching[0].vals[0]
    assert 3 == matching[0].vals[1]