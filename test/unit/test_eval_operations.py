from knowledgenet.ftypes import Eval
from knowledgenet.helper import assign, factset
from knowledgenet.rule import Evaluator, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.controls import delete, insert, update
from knowledgenet.service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1, P1, Ch1

def test_single_type_eval():
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

def test_multiple_types_eval_with_fact_inserts():
    rule_1 = Rule(id='r1',
                when=Evaluator(of_types=[P1,Ch1], 
                               matches=lambda ctx,this: assign(ctx, sum=sum([each.val for each in factset(ctx).find(of_type=P1)]) + sum([each.val for each in factset(ctx).find(of_type=Ch1)])) and ctx.sum > 0),
                then=lambda ctx: insert(ctx, R1(ctx.sum)))
    rule_2 = Rule(id='r2', order=1,
                when=Fact(of_type=P1, var='parent'),
                then=lambda ctx: insert(ctx, Ch1(ctx.parent, 10)))
    facts = [P1(10), P1(15), Eval(of_types=[P1,Ch1])]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1,rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 3 == len(matching)
    matching.sort(key=lambda r: r.vals[0])
    assert 1 == len(matching[0].vals)
    assert 25 == matching[0].vals[0]
    assert 1 == len(matching[1].vals)
    assert 35 == matching[1].vals[0]
    assert 1 == len(matching[2].vals)
    assert 45 == matching[2].vals[0]

def test_eval_with_fact_updates():
    rule_1 = Rule(id='r1',
                when=Evaluator(of_types=C1, 
                               matches=lambda ctx,this: assign(ctx, sum=sum([each.val for each in factset(ctx).find(of_type=C1)])) and ctx.sum > 0),
                then=lambda ctx: insert(ctx, R1(ctx.sum)))
    def increment(ctx):
        ctx.c1.val = ctx.c1.val+10
        update(ctx, ctx.c1)
    rule_2 = Rule(id='r2', order=1, retrigger_on_update=False,
                when=Fact(of_type=C1, var='c1'), then=increment)
    facts = [C1(10), C1(15), Eval(of_types=C1)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 3 == len(matching)
    matching.sort(key=lambda r: r.vals[0])
    assert 1 == len(matching[0].vals)
    assert 25 == matching[0].vals[0]
    assert 1 == len(matching[1].vals)
    assert 35 == matching[1].vals[0]
    assert 1 == len(matching[2].vals)
    assert 45 == matching[2].vals[0]

def test_eval_with_fact_deletes():
    rule_1 = Rule(id='r1',
                when=Evaluator(of_types=C1, 
                               matches=lambda ctx,this: assign(ctx, sum=sum([each.val for each in factset(ctx).find(of_type=C1)]))),
                then=lambda ctx: insert(ctx, R1(ctx.sum)))
    rule_2 = Rule(id='r2', order=1,
                when=Fact(of_type=C1, var='c1'), then=lambda ctx: delete(ctx, ctx.c1))
    facts = [C1(10), C1(15), Eval(of_types=C1)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 3 == len(matching)
    matching.sort(key=lambda r: r.vals[0])
    assert 1 == len(matching[0].vals)
    assert 0 == matching[0].vals[0]

    assert 1 == len(matching[1].vals)
    # This values is non-deterministic. It depends on the set
    assert matching[1].vals[0] in [10,15]

    assert 1 == len(matching[2].vals)
    assert 25 == matching[2].vals[0]

# Test with Eval updates and deletes