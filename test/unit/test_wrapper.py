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

# AI-generated code: create a pytest that tests the deletion of a Wrapper fact from a rule
def test_delete_wrapper():
    rule = Rule(id='r1',
                when=Fact(of_type='wrapper', var='w', matches=lambda ctx, this: this.val > 1),
                then=lambda ctx: delete(ctx, ctx.w))
    facts = [Wrapper(of_type='wrapper', val=1), wrapper2 := Wrapper(of_type='wrapper', val=2)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule])])).execute(facts)
    assert wrapper2 not in result_facts

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

# AI-generated code: write a pytest to test collector when a wrapper fact is removed from a rule
def test_collector_remove_wrapper():
    rule_1 = Rule(id='r1',
                    when=Fact(of_type='kickoff'),
                    then=lambda ctx: insert(ctx, 
                                            Collector(of_type='wrapper', group='sum_of_c1s', value=lambda obj: obj.wraps.val)))
    rule_2 = Rule(id='r2',
                when=Collection(group='sum_of_c1s', var='c'),
                then=lambda ctx: insert(ctx, R1(ctx.c.sum(), len(ctx.c.collection))))
    rule_3 = Rule(id='r3', order=1,
                when=Fact(of_type='wrapper', var='w', matches=lambda ctx, this: this.wraps.val == 1),
                then=lambda ctx: delete(ctx, ctx.w))
    facts = [Wrapper(of_type='kickoff'),
            wrapper1 := Wrapper(of_type='wrapper', wraps=C1(s1:=1)), 
            Wrapper(of_type='wrapper', wraps=C1(s2:=2))]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2, rule_3])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 2 == len(matching)
    matching.sort(key=lambda e: -e.vals[1])
    assert 2 == matching[0].vals[1]
    assert 1 == matching[1].vals[1]

# AI-generated code: write a pytest to test collector when a wrapper fact is updated from a rule by calling knowledgenet.controls.update() function
def test_collector_update_wrapper():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type='kickoff'),
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
                when=Fact(of_type='wrapper', var='w', matches=lambda ctx, this: this.wraps.val == 1),
                then=update_val)
    
    facts = [Wrapper(of_type='kickoff'),
            wrapper1 := Wrapper(of_type='wrapper', wraps=C1(s1:=1)), 
            Wrapper(of_type='wrapper', wraps=C1(s2:=2))]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2, rule_3])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 2 == len(matching)
    matching.sort(key=lambda e: e.vals[0])
    assert s1 + s2 == matching[0].vals[0]
    assert s1 + s2 + 1 == matching[1].vals[0]
    assert 2 == matching[0].vals[1] == matching[1].vals[1]

