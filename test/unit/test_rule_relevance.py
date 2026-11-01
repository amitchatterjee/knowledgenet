"""Phase 5 (.plans/003): Session._add_facts should skip rules whose when
clauses can't possibly match any newly-inserted fact, instead of querying
Factset.find()/_population() for every when clause of every rule on every
call. These tests pin that the skip is correctness-preserving - an
"irrelevant" rule included here never fires, and a rule that only becomes
relevant partway through a chain still fires exactly as before.
"""
from knowledgenet.container import Collector
from knowledgenet.ftypes import EventFact
from knowledgenet.rule import Collection, Event, Rule, Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert
from knowledgenet.service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, C2, R1, P1, Ch1


def test_irrelevant_rule_never_fires():
    fired = []
    rule_relevant = Rule(id='relevant',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this)),
                then=lambda ctx: insert(ctx, R1(ctx.c1.val)))
    rule_irrelevant = Rule(id='irrelevant',
                when=Fact(of_type=C2, var='c2'),
                then=lambda ctx: fired.append(ctx.c2))
    facts = [C1(10)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_relevant, rule_irrelevant])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert matching[0].vals[0] == 10
    assert fired == []


def test_rule_becomes_relevant_only_via_chained_insert():
    # rule_grandchild's only when clause is Ch1 - at the moment the initial
    # P1 fact is added, nothing in new_facts matches it, so it must start out
    # skipped and only become relevant once rule_parent's then= inserts a
    # Ch1 later in the same _add_facts-driven chain.
    rule_parent = Rule(id='parent', order=0,
                when=Fact(of_type=P1, matches=lambda ctx, this: assign(ctx, parent=this)),
                then=lambda ctx: insert(ctx, Ch1(ctx.parent, 20)))
    rule_grandchild = Rule(id='grandchild', order=1,
                when=Fact(of_type=Ch1, matches=lambda ctx, this: assign(ctx, child=this)),
                then=lambda ctx: insert(ctx, R1(ctx.child.val)))
    facts = [P1(1)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_parent, rule_grandchild])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert matching[0].vals[0] == 20


def test_collection_when_rule_relevant_via_group_key():
    fired = []
    rule_collection = Rule(id='r1',
                when=Collection(group='sum_of_c1s', matches=lambda ctx, this: assign(ctx, total=this.sum())),
                then=lambda ctx: insert(ctx, R1(ctx.total)))
    rule_irrelevant = Rule(id='irrelevant',
                when=Fact(of_type=C2, var='c2'),
                then=lambda ctx: fired.append(ctx.c2))
    facts = [C1(10), C1(15), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_collection, rule_irrelevant])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert matching[0].vals[0] == 25
    assert fired == []


def test_event_when_rule_relevant_via_group_key():
    fired = []
    rule_event = Rule(id='r1',
                when=Event(group='c1-events', matches=lambda ctx, this: assign(ctx, added=len(this.added))),
                then=lambda ctx: insert(ctx, R1(ctx.added)))
    rule_irrelevant = Rule(id='irrelevant',
                when=Fact(of_type=C2, var='c2'),
                then=lambda ctx: fired.append(ctx.c2))
    facts = [C1(10), C1(15), EventFact(group='c1-events', on_types=C1)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_event, rule_irrelevant])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert matching[0].vals[0] == 2
    assert fired == []


def test_self_join_rule_still_relevant_for_both_positions():
    # Two when clauses of the same type (self-join) - both positions must be
    # found relevant to a newly-inserted C1, independent of each other.
    rule = Rule(id='r1',
                when=[
                    Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, a=this)),
                    Fact(of_type=C1, matches=lambda ctx, this: this is not ctx.a and assign(ctx, b=this)),
                ],
                then=lambda ctx: insert(ctx, R1(ctx.a.val, ctx.b.val)))
    facts = [C1(1), C1(2)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    # (a,b) ordered pairs excluding a==b: (1,2) and (2,1)
    assert len(matching) == 2
