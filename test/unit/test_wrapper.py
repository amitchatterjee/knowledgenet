from knowledgenet.ftypes import Wrapper
from knowledgenet.rule import Collection, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert, delete, update
from knowledgenet.service import Service
from knowledgenet.container import Collector

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1

def test_kwargs_wrapper():
    rule = Rule(id='r1',
                when=Fact(of_type='wrapper', var='w', matches=lambda ctx,this: this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.w.val)))
    facts = [Wrapper(of_type='wrapper', val=1), wrapper2:=Wrapper(of_type='wrapper', val=2)]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert wrapper2.val == matching[0].vals[0]

def test_fact_wrapper():
    rule = Rule(id='r1',
                when=Fact(of_type='wrapper', var='w', matches=lambda ctx,this: this.fact.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.w.fact.val)))
    facts = [Wrapper(of_type='wrapper', fact=C1(1)), wrapper2:=Wrapper(of_type='wrapper', fact=C1(2))]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts)
    print(result_facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert wrapper2.fact.val == matching[0].vals[0]

def test_wrapper_in_collector():
    rule = Rule(id='r1',
                when=Collection(group='sum_of_c1s', var='c'),
                then=lambda ctx: insert(ctx, R1(ctx.c.sum(), len(ctx.c.collection))))
    facts = [Wrapper(of_type='wrapper', fact=C1(1)), 
            Wrapper(of_type='wrapper', fact=C1(2)),
            Collector(of_type='wrapper', group='sum_of_c1s', value=lambda obj: obj.fact.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 3 == matching[0].vals[0]
    assert 2 == matching[0].vals[1]