import sys
from collections import OrderedDict

from knowledgenet.rule import Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert, delete, update
from knowledgenet.service import Service
from knowledgenet.collector import Collector

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1, P1, Ch1

def test_collector_in_input_facts():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this: this.sum() > 10 and assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(10), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 20 == matching[0].vals[0]
    assert 2 == matching[0].vals[1]

def test_collector_filter():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this: this.sum() > 10 and assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(10), Collector(of_type=C1, group='sum_of_c1s', filter=lambda this, obj: obj.val > 10, value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 0 == len(matching)
 
def test_collector_changes_on_fact_insertion():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 10),
                  then=lambda ctx: insert(ctx, C1(1)))
    rule_2 = Rule(id='r2', order=1,
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this: this.sum() > 10 and assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 31 == matching[0].vals[0]
    assert 3 == matching[0].vals[1]

    # Change the order and this time, it should produce two results as rule 2 should run twice
    rule_1 = Rule(id='r1', order=1,
                  when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 10),
                  then=lambda ctx: insert(ctx, C1(1)))
    rule_2 = Rule(id='r2',
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this: this.sum() > 10 and assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 2 == len(matching)
    matching.sort(key=lambda o: o.vals[1])
    assert 30 == matching[0].vals[0]
    assert 2 == matching[0].vals[1]
    assert 31 == matching[1].vals[0]
    assert 3 == matching[1].vals[1]

def test_collector_changes_on_fact_deletion():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 10 and assign(ctx, obj=this)),
                  then=lambda ctx: delete(ctx, ctx.obj))
    rule_2 = Rule(id='r2', order=1,
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this:  assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 10 == matching[0].vals[0]
    assert 1 == matching[0].vals[1]

    rule_1 = Rule(id='r1', order=1,
                  when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 10 and assign(ctx, obj=this)),
                  then=lambda ctx: delete(ctx, ctx.obj))
    rule_2 = Rule(id='r2',
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this:  assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 2 == len(matching)
    matching.sort(key=lambda o: o.vals[1])
    assert 10 == matching[0].vals[0]
    assert 1 == matching[0].vals[1]
    assert 30 == matching[1].vals[0]
    assert 2 == matching[1].vals[1]

def test_collector_changes_on_fact_updates():
    def divide_by_2(ctx):
        ctx.obj.val = ctx.obj.val // 2
        update(ctx, ctx.obj)
    rule_1 = Rule(id='r1', retrigger_on_update=False,
                  when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, obj=this)),
                  then=divide_by_2)
    rule_2 = Rule(id='r2', order=1,
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this:  assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(50), C1(10), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 30 == matching[0].vals[0]
    assert 2 == matching[0].vals[1]

    rule_1 = Rule(id='r1', retrigger_on_update=False, order=1,
                  when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, obj=this)),
                  then=divide_by_2)
    rule_2 = Rule(id='r2', 
                when=Fact(of_type=Collector, group='sum_of_c1s', matches=lambda ctx, this:  assign(ctx, sum=this.sum(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(50), C1(10), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 3 == len(matching)
    matching.sort(key=lambda o: o.vals[0], reverse=True)
    # The first element (after sorting) is always 50+10
    assert 50+10 == matching[0].vals[0]
    # Depending on whether r1 was triggered by C1 or C2, we will get different outcomes. If C1 triggered first, then the value is 25+10. If C2 was triggered first, then the value is 50+5
    assert matching[1].vals[0] in [25+10,50+5]
    # The last iteration will always be 30
    assert 30 == matching[2].vals[0]

def test_collector_insert_from_rule():
    '''
    For each object of type P1, create a collector that keeps track of all objects of type Ch1 that refers to it
    '''
    rule_1 = Rule(id='r1',
                when=Fact(of_type=P1, matches=lambda ctx, this: assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, Collector(of_type=Ch1, group='child', parent=ctx.parent, filter=lambda this, child: child.parent == this.parent)))
    p1 = P1(1)
    p2 = P1(2)
    facts = [p1, Ch1(p1,10), Ch1(p1,11), p2, Ch1(p2,20), Ch1(p2,21)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
    matching = find_result_of_type(Collector, result_facts)
    assert 2 == len(matching)
    result = sort_collectors(matching)
    assert(OrderedDict([(1, [10, 11]), (2, [20, 21])]) == result)

def test_complex_interactions_with_collectors():
    '''
    For each object of type P1, create a collector that keeps track of all objects of type Ch1 that refers to it
    '''
    rule_1 = Rule(id='r1',
                when=Fact(of_type=P1, matches=lambda ctx,this: assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, 
                                        Collector(of_type=Ch1, group='child', parent=ctx.parent, 
                                            filter=lambda this,child: child.parent == this.parent, 
                                            value=lambda obj: obj.val)))
    def add_3_children(ctx):
        insert(ctx, Ch1(ctx.parent, ctx.parent.val*10))
        insert(ctx, Ch1(ctx.parent, ctx.parent.val*10+1))
        insert(ctx, Ch1(ctx.parent, ctx.parent.val*10+2))
    '''
    For each object of type P1, add 3 objects of type Ch1 that refers to it. Note the order.
    '''
    rule_2 = Rule(id='r2', order=1,
                when=Fact(of_type=P1, matches=lambda ctx, this: assign(ctx, parent=this)),
                then=add_3_children)
    
    '''
    For each object of type P1 with obj.val = 1, match the corresponding collector that contains atleast three objects in it's collection. Note the order = 0. This rule should not fire unless rule_2 is invoked.
    '''
    rule_3 = Rule(id='r3',
                when=[
                    Fact(of_type=P1, matches=lambda ctx, this: this.val == 1 and assign(ctx, p=this)),
                    Fact(of_type=Collector, group='child', 
                              matches=lambda ctx, this: this.parent == ctx.p and len(this.collection) >=3  and assign(ctx, collector=this))],
                then=lambda ctx: insert(ctx, R1(ctx.p.val, ctx.collector.sum())))
    facts = [P1(1), P1(2)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2, rule_3])])).execute(facts)
    matching = find_result_of_type(Collector, result_facts)
    assert 2 == len(matching)
    result = sort_collectors(matching)
    assert(OrderedDict([(1, [10, 11, 12]), (2, [20, 21, 22])]) == result)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert R1 == type(matching[0])
    assert 1 == matching[0].vals[0]
    assert 10+11+12 == matching[0].vals[1]

def test_variance_in_collector():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=Collector, group='c1s', matches=lambda ctx,this:assign(ctx, sum=this.sum(), variance=this.variance(), size=len(this.collection))),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.variance, ctx.size)))
    facts = [C1(10), C1(20), C1(30), C1(40), C1(50), 
             Collector(of_type=C1, group='c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 150 == matching[0].vals[0]
    assert 250 == matching[0].vals[1]
    assert 5 == matching[0].vals[2]

def test_minmax_in_collector():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=Collector, group='c1s', 
                               matches=lambda ctx,this:assign(ctx, sum=this.sum(),
                               variance=this.variance(), size=len(this.collection), min=this.minimum(), max=this.maximum())),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.variance, ctx.size, ctx.min, ctx.max)))
    facts = [C1(10), C1(20), C1(30), C1(40), C1(50), 
             Collector(of_type=C1, group='c1s', 
                       value=lambda obj: obj.val, 
                       key=lambda o: o.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1 == len(matching)
    assert 150 == matching[0].vals[0]
    assert 250 == matching[0].vals[1]
    assert 5 == matching[0].vals[2]
    assert facts[0] is matching[0].vals[3]
    assert facts[-2] is matching[0].vals[4]

def sort_collectors(matching):
    matching.sort(key=lambda e: e.parent.val)
    result = OrderedDict()
    for each in matching:
        l = list(each.collection)
        l.sort(key=lambda e: e.val)
        l = [i.val for i in l]
        result[each.parent.val] = l
    return result
