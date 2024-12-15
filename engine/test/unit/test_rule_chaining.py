from rule import Rule,Condition
from ruleset import Ruleset
from repository import Repository
from helper import assign
from controls import insert, update, delete
from service import execute

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1, P1, Ch1

def test_rule_chaining_with_insert():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, Ch1(ctx.parent, 20)))
    rule_2 = Rule(id='r2',
                when=Condition(of_type=Ch1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, child=this)),
                then=lambda ctx: insert(ctx, R1(ctx.child.parent, ctx.child)))
    
    facts = [P1(20)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]
    assert Ch1 == type(matching[0].vals[1])

def test_rule_chaining_with_insert_and_matching():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, Ch1(ctx.parent, 20)))
    rule_2 = Rule(id='r2', 
                    when=[
                        Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                        Condition(of_type=Ch1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and ctx.child.parent == ctx.parent)],
                then=lambda ctx: insert(ctx, R1(ctx.parent, ctx.child)))
    facts = [P1(20)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 2 ==len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]
    assert Ch1 == type(matching[0].vals[1])

def test_rule_chaining_with_update():
    def zero_out(ctx):
        ctx.c1.val = 0
        update(ctx, ctx.c1)
    rule_1 = Rule(id='r1',
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, c1=this)),
                then=zero_out)
    rule_2 = Rule(id='r2',
                when=Condition(of_type=C1, matches_exp=lambda ctx, this: this.val <= 0 and assign(ctx, c2=this)),
                then=lambda ctx: insert(ctx, R1(ctx.c2)))    
    facts = [C1(20)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 1 ==len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]

def test_rule_chaining_with_delete():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                then=lambda ctx: delete(ctx, ctx.parent))
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                    Condition(of_type=Ch1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and this.parent == ctx.parent)],
                then=lambda ctx: insert(ctx, R1(ctx.parent, ctx.child)))
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 0 == len(matching)

def test_chaining_with_walkback_on_insert():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=R1, matches_exp=lambda ctx, this: assign(ctx, result=this)),
                then=lambda ctx: delete(ctx, ctx.result))    
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                    Condition(of_type=Ch1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and this.parent == ctx.parent)],
                then=lambda ctx: insert(ctx, R1(ctx.parent, ctx.child)))
 
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 0 == len(matching)

def test_chaining_with_walkback_on_update():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=P1, matches_exp=lambda ctx, this: this.val <= 0 and assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, R1(ctx.parent)))
    def rule_2_then(ctx):
        ctx.parent.val = 0
        update(ctx, ctx.parent)  
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, parent=this)),
                    Condition(of_type=Ch1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx, child=this) and this.parent == ctx.parent)],
                then=rule_2_then)
 
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(R1, result_facts)
    assert 1==len(matching)
    assert 1 ==len(matching[0].vals)
    assert facts[0] == matching[0].vals[0]

def test_chaining_with_walkback_on_delete():
    rule_1 = Rule(id='r1',
                when=Condition(of_type=Ch1, matches_exp=lambda ctx, this: not this.parent and assign(ctx, orphan=this)),
                then=lambda ctx: delete(ctx, ctx.orphan))
    def rule_2_then(ctx):
        # Delete the parent and make the child an orpan
        ctx.child.parent = None
        update(ctx, ctx.child)
        delete(ctx, ctx.parent)
    rule_2 = Rule(id='r2', order=1,
                when=[
                    Condition(of_type=P1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,parent=this)),
                    Condition(of_type=Ch1, matches_exp=lambda ctx, this: this.val > 0 and assign(ctx,child=this) and this.parent == ctx.parent)],
                then=rule_2_then)
    parent = P1(20)
    facts = [parent, Ch1(parent, 20)]
    result_facts = execute(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])]), facts)
    matching = find_result_of_type(P1, result_facts)
    assert 0 == len(matching)
    matching = find_result_of_type(Ch1, result_facts)
    assert 0 == len(matching)
