from rule import Rule,Condition
from ruleset import Ruleset
from repository import Repository
from helper import assign
from controls import insert, update, next_ruleset
from service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, C2, R1

def test_flow_control_with_run_once():
    def rule_1_then(ctx):
        ctx.c1.val = 0
        update(ctx, ctx.c1)
    rule_1 = Rule(id='r1', run_once=True,
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, c1=this)),
                then=rule_1_then)
    def rule_2_then(ctx):
        ctx.c2.val = 1
        update(ctx, ctx.c2)
    rule_2 = Rule(id='r2',
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: this.val <= 0 and assign(ctx, c2=this)),
                then=rule_2_then)    
    facts = [C1(20)]
    Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    # If we are here, it means we are not in an infinite loop. That implies, rule 1 has fired only once because of run_once=True

def test_flow_control_with_no_retrigger_on_update():
    def rule_1_then(ctx):
        insert(ctx, R1(ctx.c.val))
        ctx.c.val = 0
        update(ctx, ctx.c)
    rule_1 = Rule(id='r1', retrigger_on_update=False,
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: assign(ctx, c=this)),
                then=rule_1_then)
    def rule_2_then(ctx):
        ctx.c.val = 10
        update(ctx, ctx.c)
    rule_2 = Rule(id='r2', run_once=True,
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: assign(ctx, c=this)),
                then=rule_2_then)
    facts = [C1(20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', 
                                                        [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 2 ==len(matching)
    matching.sort(key=lambda o: o.vals[0])
    assert 10 == matching[0].vals[0]
    assert 20 == matching[1].vals[0]

def test_flow_control_with_next_ruleset():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this)),
                then=lambda ctx: insert(ctx, C2(ctx.c1.val)))
    rule_2 = Rule(id='r2',
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: this.val > 10),
                then=lambda ctx: next_ruleset(ctx))
    rule_3 = Rule(id='r3', order=1,
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: assign(ctx, c2=this)),
                then=lambda ctx: insert(ctx, R1(ctx.c2.val)))
    facts = [C1(20)]
    result_facts=Service(Repository('repo1', 
                                    [Ruleset('rs1', [rule_1, rule_2, rule_3])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 0 == len(matching)