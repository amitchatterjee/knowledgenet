from knowledgenet.controls import insert
from knowledgenet.helper import assign
from knowledgenet.rule import Fact, Rule
from knowledgenet.scanner import ruledef
from test_helpers.unit_facts import C1, R1

@ruledef(id='rule-override', ruleset='ruleset-override', repository='repo-override')
def rule2():
    return Rule(when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val <= 10),
        then=lambda ctx: insert(ctx, R1(ctx.c1, 'repo2')))