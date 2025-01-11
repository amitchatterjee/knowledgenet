import json
import logging
import io

from knowledgenet.collector import Collector
from knowledgenet.rule import Collection, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert
from knowledgenet.service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, C2, R1

def test_one_rule_single_when_then():
    rule = Rule(id='r1',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert facts[1] == matching[0].vals[0]

def test_one_rule_multiple_when_thens():
    rule = Rule(id='r1', when=[
                Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                Fact(of_type=C2, matches=lambda ctx, this: assign(ctx, c2=this) and this.val != ctx.c1.val and this.val > 1)],
                then=[
                    lambda ctx: logging.info(f"Found match: {(ctx.c1,ctx.c2)}"),
                    lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2))])

    facts = [C1(1), C1(2), C2(1), C2(2), C2(3)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert (facts[1],facts[4]) == matching[0].vals

def test_condition_with_python_collection_objs():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=tuple, matches=lambda ctx, this: assign(ctx, l=this) and len(this) >= 2),
                then=lambda ctx: insert(ctx, R1(ctx.l)))
    rule_2 = Rule(id='r2',
                when=Fact(of_type=frozenset, matches=lambda ctx, this: assign(ctx, d=this) and 'name' in this),
                then=lambda ctx: insert(ctx, R1(ctx.d)))
    facts = [(C1(1), C1(2)), frozenset({'name': 'tester'})]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts,)
    matching = find_result_of_type(R1, result_facts)
    matching.sort(key=lambda o: str(o)) # Sort to make the order predictable
    assert 2== len(matching)
    assert 1 == len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]
    assert 1 == len(matching[1].vals)
    assert facts[1] == matching[1].vals[0]

def test_multiple_matches_syntax():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type=C1, matches=lambda ctx,this: this.val > 10),
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

def test_tracer():
    rule = Rule(id='r1',
                when=Fact(of_type=C1, var='c1', matches=lambda ctx, this: this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    with io.StringIO() as stream:
        Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts, tracer=stream)
        trace = stream.getvalue()
        parsed = json.loads(trace)
        assert list == type(parsed)
        assert 1 == len(parsed)
        assert dict == type(parsed[0])
