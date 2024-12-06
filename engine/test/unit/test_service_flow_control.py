from rule import Rule,Condition
from ruleset import Ruleset
from repository import Repository
from helper import assign
from notify import insert, end, switch
from service import execute

from test_helpers.test_util import find_result_of_type
from test_helpers.test_facts import C1, C2, R1

def test_flow_control_with_end():
    rule_1_1 = Rule(id='r11',
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this)),
                then=lambda ctx: insert(ctx, C2(ctx.c1.val)))
    rule_1_2 = Rule(id='r12',
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: this.val > 10),
                then=lambda ctx: end(ctx))
    rule_1_3 = Rule(id='r13', rank=1,
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: True),
                then=lambda ctx: insert(ctx, R1('r13')))
    
    rule_2_1 = Rule(id='r21',
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: True),
                then=lambda ctx: insert(ctx, R1('r21')))

    facts = [C1(20)]
    repo = Repository('repo1', [
        Ruleset('rs1', [rule_1_1, rule_1_2, rule_1_3]), 
        Ruleset('rs2', [rule_2_1])])

    result_facts=execute(repo, facts)
    matching = find_result_of_type(R1, result_facts)
    assert 0 == len(matching)

    facts = [C1(0)]
    result_facts=execute(repo, facts)
    matching = find_result_of_type(R1, result_facts)
    assert 2 == len(matching)
    matching.sort(key=lambda e: e.vals[0])
    assert 'r13' == matching[0].vals[0]
    assert 'r21' == matching[1].vals[0]
    # TODO this is not working properly. Looks like there is an issue with leftmost computation. Look into it and fix it

def test_flow_control_with_switch():
    rule_1_1 = Rule(id='r11',
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this)),
                then=lambda ctx: insert(ctx, C2(ctx.c1.val)))
    rule_1_2 = Rule(id='r12',
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: this.val > 10),
                then=lambda ctx: switch(ctx, 'rs3'))
    rule_1_3 = Rule(id='r13', rank=1,
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: assign(ctx, c2=this)),
                then=lambda ctx: insert(ctx, R1(ctx.c2.val)))
    
    rule_2_1 = Rule(id='r21',
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: True),
                then=lambda ctx: insert(ctx, R1('r21')))
    
    rule_3_1 = Rule(id='r31',
                when=Condition(of_type=C2, matches_exp=lambda ctx, this: True),
                then=lambda ctx: insert(ctx, R1('r31')))

    facts = [C1(20)]
    result_facts=execute(Repository('repo1', [
        Ruleset('rs1', [rule_1_1, rule_1_2, rule_1_3]), 
        Ruleset('rs2', [rule_2_1]),
        Ruleset('rs3', [rule_3_1])]), 
        facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 'r31' == matching[0].vals[0]
