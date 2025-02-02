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

def test_wrapper_in_collector():
    rule = Rule(id='r1',
                when=Collection(group='sum_of_c1s', var='c'),
                then=lambda ctx: insert(ctx, R1(ctx.c.sum(), len(ctx.c.collection))))
    facts = [Wrapper(of_type='wrapper', wraps=C1(s1:=1)), 
            Wrapper(of_type='wrapper', wraps=C1(s2:=2)),
            Collector(of_type='wrapper', group='sum_of_c1s', value=lambda obj: obj.wraps.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert s1+s2 == matching[0].vals[0]
    assert 2 == matching[0].vals[1]

def test_collector_insert_in_rule():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type='kickoff'),
                  then=lambda ctx: insert(ctx, 
                                          Collector(of_type='wrapper', group='sum_of_c1s', value=lambda obj: obj.wraps.val)))
    rule_2 = Rule(id='r2',
                when=Collection(group='sum_of_c1s', var='c'),
                then=lambda ctx: insert(ctx, R1(ctx.c.sum(), len(ctx.c.collection))))
    facts = [Wrapper(of_type='kickoff'),
            Wrapper(of_type='wrapper', wraps=C1(s1:=1)), 
            Wrapper(of_type='wrapper', wraps=C1(s2:=2))]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1,rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert s1+s2 == matching[0].vals[0]
    assert 2 == matching[0].vals[1]