from scanner import ruledef
from rule import Rule, Condition
from notify import insert
from helper import assign

from test.functional.test_helpers.test_facts import C1, R1

@ruledef
def rule1():
    return Rule(id='r1', service='ts1', ruleset='rs1',
        when=Condition(for_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this) and this.val <= 10),
        then=lambda ctx: insert(ctx, R1(ctx.c1, 'small')))

@ruledef
def rule2():
     return Rule(id='r2', service='ts1', ruleset='rs1',
        when=Condition(for_type=C1, matches_exp=lambda ctx, this: assign(ctx, c1=this) and this.val > 10),
        then=lambda ctx: insert(ctx, R1(ctx.c1, 'large')))

def somethingelse():
    pass