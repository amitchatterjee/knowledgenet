from knowledgenet.scanner import ruledef
from knowledgenet.rule import Rule, Condition
from knowledgenet.controls import insert
from knowledgenet.helper import assign

from test_helpers.unit_facts import C1, R1

@ruledef
def rule1():
    return Rule(when=Condition(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val <= 10),
        then=lambda ctx: insert(ctx, R1(ctx.c1, 'small')))

@ruledef
def rule2():
    def set_as_large(ctx):
        insert(ctx, R1(ctx.c1, 'large'))
    return Rule(when=Condition(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 10),
    then=set_as_large)

# This should not scan
def rule3():
    def set_as_large(ctx):
        insert(ctx, R1(ctx.c1, 'large'))
    return Rule(when=Condition(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 10),
    then=set_as_large)