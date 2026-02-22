
from knowledgenet.node import Node
from knowledgenet.rule import Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.service import Service

from test_helpers.unit_facts import C1

def node_sorter_asc(n1:Node,n2:Node)->int:
    # Order by ascending order of node value (instead of rule order)
    return n1.when_objs[0].val - n2.when_objs[0].val

def node_sorter_desc(n1:Node,n2:Node)->int:
    # Order by descending order of node value (instead of rule order)
    return n2.when_objs[0].val - n1.when_objs[0].val

def test_node_sorting_ascending_value():
    execution_order = []
    rule = Rule(id='r1',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this)),
                then=lambda ctx: execution_order.append(ctx.c1))
    facts = [C1(10), C1(2), C1(1)]
    Service(Repository('repo1',[Ruleset('rs1', [rule])]), node_sorter=node_sorter_asc).execute(facts)
    size = len(execution_order)
    assert 3 == size
    for i,each in enumerate(execution_order):
        assert each == facts[size-i-1]

def test_node_sorting_descending_value():
    execution_order = []
    rule = Rule(id='r1',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this)),
                then=lambda ctx: execution_order.append(ctx.c1))
    facts = [C1(10), C1(2), C1(1)]
    Service(Repository('repo1',[Ruleset('rs1', [rule])]), node_sorter=node_sorter_desc).execute(facts)
    size = len(execution_order)
    assert 3 == size
    for i,each in enumerate(execution_order):
        assert each == facts[i]