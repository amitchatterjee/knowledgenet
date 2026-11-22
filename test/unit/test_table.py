from types import SimpleNamespace

import pytest

from knowledgenet.ftypes import Table, Row
from knowledgenet.helper import assign
from knowledgenet.controls import insert
from knowledgenet.rule import Rule, Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import R1

# --- Construction / Row basics ---------------------------------------------

def test_add_row_sets_table_and_sequential_index():
    table = Table('t1')
    table.add_row((1, 2))
    table.add_row((3, 4))
    assert [row.index for row in table.rows] == [0, 1]
    assert [row.columns for row in table.rows] == [(1, 2), (3, 4)]
    assert all(row.table is table for row in table.rows)

def test_rows_passed_to_constructor_are_wrapped():
    table = Table('t1', rows=((1, 2), (3, 4), (5, 6)))
    assert len(table.rows) == 3
    assert [row.columns for row in table.rows] == [(1, 2), (3, 4), (5, 6)]

def test_empty_table_has_no_rows():
    table = Table('t1')
    assert table.rows == []

def test_row_equality_and_hash_are_based_on_table_and_index_only():
    table = Table('t1', rows=((1, 2), (3, 4)))
    same_position_different_data = Row(table, columns=('x', 'y'), index=0)
    assert same_position_different_data == table.rows[0]
    assert hash(same_position_different_data) == hash(table.rows[0])
    assert table.rows[0] != table.rows[1]

# --- kickoff -----------------------------------------------------------------

def test_kickoff_run_sequentially_inserts_only_first_row():
    table = Table('t1', rows=((1,), (2,), (3,)))
    facts = []
    table.kickoff(facts)
    assert facts == [table.rows[0]]
    assert table.next_index == 1

def test_kickoff_run_all_inserts_every_row():
    table = Table('t1', run_all=True, rows=((1,), (2,), (3,)))
    facts = []
    table.kickoff(facts)
    assert facts == table.rows

def test_kickoff_accepts_a_set():
    table = Table('t1', rows=((1,), (2,), (3,)))
    facts = set()
    table.kickoff(facts)
    assert facts == {table.rows[0]}

def test_kickoff_on_empty_table_is_a_noop():
    table = Table('t1')
    facts = []
    table.kickoff(facts)
    assert facts == []

# --- next() ------------------------------------------------------------------

def test_next_raises_on_run_all_table():
    table = Table('t1', run_all=True, rows=((1,),))
    ctx = SimpleNamespace(_changes={})
    with pytest.raises(Exception):
        table.next(ctx)

def test_next_walks_through_remaining_rows_in_order():
    table = Table('t1', rows=((1,), (2,), (3,)))
    facts = []
    table.kickoff(facts)
    ctx = SimpleNamespace(_changes={})

    table.next(ctx)
    assert ctx._changes['insert'] == [table.rows[1]]

    ctx._changes = {}
    table.next(ctx)
    assert ctx._changes['insert'] == [table.rows[2]]

def test_next_is_a_safe_noop_once_rows_are_exhausted():
    table = Table('t1', rows=((1,), (2,)))
    facts = []
    table.kickoff(facts)
    ctx = SimpleNamespace(_changes={})

    assert table.next(ctx) is True  # advances to row 1
    ctx._changes = {}
    assert table.next(ctx) is True  # no more rows, nothing queued
    assert ctx._changes == {}
    # Calling again stays safe
    assert table.next(ctx) is True
    assert ctx._changes == {}

def test_next_on_single_row_table_is_a_noop():
    table = Table('t1', rows=((1,),))
    facts = []
    table.kickoff(facts)
    ctx = SimpleNamespace(_changes={})
    table.next(ctx)
    assert ctx._changes == {}

# --- Rule-driven end-to-end scenarios ---------------------------------------

def test_run_sequentially_driven_from_then():
    """Each row is processed one at a time; the `then` clause advances the
    table to the next row only after recording the current one."""
    table = Table('seq', rows=((1,), (2,), (3,)))
    facts = []
    table.kickoff(facts)

    def process(ctx):
        insert(ctx, R1(ctx.row.columns))
        table.next(ctx)

    rule = Rule(id='process_row',
                when=Fact(of_type=Row, matches=lambda ctx, this: this.table.name == 'seq' and assign(ctx, row=this)),
                then=process)

    result_facts = Service(Repository('repo', [Ruleset('rs', [rule])])).execute(facts)
    results = find_result_of_type(R1, result_facts)
    assert sorted(r.vals[0] for r in results) == [(1,), (2,), (3,)]

def test_run_sequentially_driven_from_when():
    """`next()` is called as part of the when-clause's match expression
    instead of the then clause."""
    table = Table('seq', rows=((1,), (2,), (3,)))
    facts = []
    table.kickoff(facts)

    rule = Rule(id='process_row',
                when=Fact(of_type=Row, matches=lambda ctx, this:
                          this.table.name == 'seq' and assign(ctx, row=this) and table.next(ctx)),
                then=lambda ctx: insert(ctx, R1(ctx.row.columns)))

    result_facts = Service(Repository('repo', [Ruleset('rs', [rule])])).execute(facts)
    results = find_result_of_type(R1, result_facts)
    assert sorted(r.vals[0] for r in results) == [(1,), (2,), (3,)]

def test_run_all_processes_every_row_independently():
    """run_all tables hand every row to the engine up front; no next() is
    needed or allowed."""
    table = Table('all', run_all=True, rows=((1,), (2,), (3,)))
    facts = []
    table.kickoff(facts)

    rule = Rule(id='process_row',
                when=Fact(of_type=Row, matches=lambda ctx, this: this.table.name == 'all' and assign(ctx, row=this)),
                then=lambda ctx: insert(ctx, R1(ctx.row.columns)))

    result_facts = Service(Repository('repo', [Ruleset('rs', [rule])])).execute(facts)
    results = find_result_of_type(R1, result_facts)
    assert sorted(r.vals[0] for r in results) == [(1,), (2,), (3,)]
