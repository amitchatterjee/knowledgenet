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

def test_rule_with_simple_wrapper():
    rule = Rule(id='r1',
                when=Fact(of_type='wrapper', var='w', matches=lambda ctx,this: this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.w.val)))
    facts = [Wrapper(of_type='wrapper', val=1), wrapper2:=Wrapper(of_type='wrapper', val=2)]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    print(matching)
    assert 1== len(matching)
    assert 1 == len(matching[0].vals)
    assert wrapper2.val == matching[0].vals[0]

