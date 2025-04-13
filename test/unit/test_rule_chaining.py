import sys
from knowledgenet.rule import Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert, update, delete
from knowledgenet.service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1, P1, Ch1

def test_rule_chaining_with_insert():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, Ch1(ctx.parent, 20)))
    rule_2 = Rule(id='r2',
                when=Fact(of_type=Ch1, matches=lambda ctx, this: this.val > 0 and assign(ctx, child=this)),
                then=lambda ctx: insert(ctx, R1(ctx.child.parent, ctx.child)))
    
    facts = [P1(20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching)==1
    assert len(matching[0].vals)==2
    assert matching[0].vals[0]==facts[0]
    assert type(matching[0].vals[1])==Ch1

def test_rule_chaining_with_insert_and_matching():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, Ch1(ctx.parent, 20)))
    rule_2 = Rule(id='r2', 
                    when=[
                        Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                        Fact(of_type=Ch1, matches=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and ctx.child.parent == ctx.parent)],
                then=lambda ctx: insert(ctx, R1(ctx.parent, ctx.child)))
    facts = [P1(20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching)==1
    assert len(matching[0].vals)==2
    assert matching[0].vals[0]==facts[0]
    assert type(matching[0].vals[1])==Ch1

def test_rule_chaining_with_update():
    def zero_out(ctx):
        ctx.c1.val = 0
        update(ctx, ctx.c1)
    rule_1 = Rule(id='r1',
                when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 0 and assign(ctx, c1=this)),
                then=zero_out)
    rule_2 = Rule(id='r2',
                when=Fact(of_type=C1, matches=lambda ctx, this: this.val <= 0 and assign(ctx, c2=this)),
                then=lambda ctx: insert(ctx, R1(ctx.c2)))    
    facts = [C1(20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching)==1
    assert len(matching[0].vals)==1
    assert matching[0].vals[0]==facts[0]

def test_rule_chaining_with_delete():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                then=lambda ctx: delete(ctx, ctx.parent))
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                    Fact(of_type=Ch1, matches=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and this.parent == ctx.parent)],
                then=lambda ctx: insert(ctx, R1(ctx.parent, ctx.child)))
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching)==0

def test_chaining_with_walkback_on_insert():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=R1, matches=lambda ctx, this: assign(ctx, result=this)),
                then=lambda ctx: delete(ctx, ctx.result))    
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                    Fact(of_type=Ch1, matches=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and this.parent == ctx.parent)],
                then=lambda ctx: insert(ctx, R1(ctx.parent, ctx.child)))
 
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching)==0

def test_chaining_with_walkback_on_update():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=P1, matches=lambda ctx, this: this.val <= 0 and assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, R1(ctx.parent)))
    def rule_2_then(ctx):
        ctx.parent.val = 0
        update(ctx, ctx.parent)  
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                    Fact(of_type=Ch1, matches=lambda ctx, this: this.val > 0 and assign(ctx, child=this) and this.parent == ctx.parent)],
                then=rule_2_then)
 
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching)==1
    assert len(matching[0].vals)==1
    assert matching[0].vals[0]==facts[0]

def test_chaining_with_walkback_on_delete():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=Ch1, matches=lambda ctx, this: not this.parent and assign(ctx, orphan=this)),
                then=lambda ctx: delete(ctx, ctx.orphan))
    def rule_2_then(ctx):
        # Delete the parent and make the child an orpan
        ctx.child.parent = None
        update(ctx, ctx.child)
        delete(ctx, ctx.parent)
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Fact(of_type=P1, matches=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                    Fact(of_type=Ch1, matches=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and this.parent == ctx.parent)],
                then=rule_2_then)
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(P1, result_facts)
    assert len(matching)==0
    matching = find_result_of_type(Ch1, result_facts)
    assert len(matching)==0

def test_multiple_combinations():
    rule_1 = Rule(id='r1',
                when=[Fact(of_type=P1, matches=lambda ctx, this: assign(ctx, parent=this)),
                    Fact(of_type=Ch1, matches=lambda ctx, this: this.parent == ctx.parent and assign(ctx, child=this))],
                then=lambda ctx: insert(ctx, R1(ctx.parent, ctx.child)))
    p1 = P1(1)
    p2 = P1(2)
    facts = [p1, Ch1(p1,1), Ch1(p1,2), p2, Ch1(p2,1), Ch1(p2,2)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching)==4
    matching.sort(key=lambda each: each.vals[0].val * 10 + each.vals[1].val)
    assert [(e.vals[0].val, e.vals[1].val) for e in matching]==[(1, 1), (1, 2), (2, 1), (2, 2)]