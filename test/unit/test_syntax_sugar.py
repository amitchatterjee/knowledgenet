from knowledgenet.ftypes import Wrapper
from knowledgenet.rule import Collection, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert, delete, update
from knowledgenet.service import Service
from knowledgenet.container import Collector

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1, P1, Ch1

def test_rule_with_when_var():
    rule = Rule(id='r1',
                when=Fact(of_type=C1, var='c1', matches=lambda ctx,this: this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert len(matching[0].vals) == 1
    assert matching[0].vals[0] == facts[1]

def test_collector_syntax():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type=C1, matches=lambda ctx,this: this.val > 10),
                  then=lambda ctx: insert(ctx, C1(1)))
    rule_2 = Rule(id='r2', order=1,
                when=Collection(group='sum_of_c1s', matches=lambda ctx, this: this.sum() > 10 and assign(ctx, sum=this.sum(), size=this.size())),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert matching[0].vals[0] == 31
    assert matching[0].vals[1] == 3

def test_collector_update_wrapper():
    rule_1 = Rule(id='r1',
                  when=Fact(named='kickoff'),
                  then=lambda ctx: insert(ctx, 
                                          Collector(of_type='wrapper', group='sum_of_c1s', 
                                                    value=lambda obj: obj.wraps.val)))
    rule_2 = Rule(id='r2',
                when=Collection(group='sum_of_c1s', var='c'),
                then=lambda ctx: insert(ctx, R1(ctx.c.sum(), len(ctx.c.collection))))
    def update_val(ctx):
        ctx.w.wraps.val=ctx.w.wraps.val+1
        update(ctx, ctx.w)
    rule_3 = Rule(id='r3', order=1, retrigger_on_update=False,
                when=Fact(named='wrapper', var='w', matches=lambda ctx, this: this.wraps.val == 1),
                then=update_val)
    
    facts = [Wrapper(named='kickoff'),
            Wrapper(named='wrapper', wraps=C1(s1:=1)), 
            Wrapper(named='wrapper', wraps=C1(s2:=2))]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2, rule_3])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 2
    matching.sort(key=lambda e: e.vals[0])
    assert matching[0].vals[0] == s1 + s2
    assert matching[1].vals[0] == s1 + s2 + 1
    assert matching[0].vals[1] == matching[1].vals[1] == 2