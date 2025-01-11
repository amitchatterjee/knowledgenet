from knowledgenet.ftypes import Eval
from knowledgenet.helper import assign, factset
from knowledgenet.rule import Evaluator, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.controls import insert
from knowledgenet.service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1, P1, Ch1

def test_basic_eval():
    rule_1 = Rule(id='r1',
                when=Evaluator(of_types=C1, 
                               matches=lambda ctx,this: assign(ctx, sum=sum([each.val for each in factset(ctx).find(of_type=C1)])) and ctx.sum > 0),
                then=lambda ctx: insert(ctx, R1(ctx.sum)))
    facts = [C1(10), C1(15), Eval(of_types=C1)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 1 == len(matching[0].vals)
    assert 25 == matching[0].vals[0]