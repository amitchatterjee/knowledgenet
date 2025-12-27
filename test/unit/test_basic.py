import json
import logging
import io

from knowledgenet.container import Collector
from knowledgenet.core.file_trace_exporter import FileSpanExporter
from knowledgenet.rule import Collection, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert
from knowledgenet.service import Service
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry import trace

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, C2, R1
import os

def test_one_rule_single_when_then():
    rule = Rule(id='r1',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    result_facts = Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert len(matching[0].vals) == 1
    assert matching[0].vals[0] == facts[1]

def test_one_rule_multiple_when_thens():
    rule = Rule(id='r1', when=[
                Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                Fact(of_type=C2, matches=lambda ctx, this: assign(ctx, c2=this) and this.val != ctx.c1.val and this.val > 1)],
                then=[
                    lambda ctx: logging.info(f"Found match: {(ctx.c1,ctx.c2)}"),
                    lambda ctx: insert(ctx, R1(ctx.c1,ctx.c2))])

    facts = [C1(1), C1(2), C2(1), C2(2), C2(3)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert len(matching[0].vals) == 2
    assert matching[0].vals == (facts[1],facts[4])

def test_condition_with_python_collection_objs():
    rule_1 = Rule(id='r1',
                when=Fact(of_type=tuple, matches=lambda ctx, this: assign(ctx, l=this) and len(this) >= 2),
                then=lambda ctx: insert(ctx, R1(ctx.l)))
    rule_2 = Rule(id='r2',
                when=Fact(of_type=frozenset, matches=lambda ctx, this: assign(ctx, d=this) and 'name' in this),
                then=lambda ctx: insert(ctx, R1(ctx.d)))
    facts = [(C1(1), C1(2)), frozenset({'name': 'tester'})]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts,)
    matching = find_result_of_type(R1, result_facts)
    matching.sort(key=lambda o: str(o)) # Sort to make the order predictable
    assert len(matching) == 2
    assert len(matching[0].vals) == 1
    assert matching[0].vals[0] == facts[0]
    assert len(matching[1].vals) == 1
    assert matching[1].vals[0] == facts[1]

def test_multiple_matches_syntax():
    rule_1 = Rule(id='r1',
                  when=Fact(of_type=C1, matches=lambda ctx,this: this.val > 10),
                  then=lambda ctx: insert(ctx, C1(1)))
    rule_2 = Rule(id='r2', order=1,
                when=Collection(group='sum_of_c1s', 
                        matches=[lambda ctx,this: this.sum() > 10, 
                                 lambda ctx,this: assign(ctx, sum=this.sum(), size=this.size())]),
                then=lambda ctx: insert(ctx, R1(ctx.sum, ctx.size)))
    facts = [C1(10), C1(20), Collector(of_type=C1, group='sum_of_c1s', value=lambda obj: obj.val)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule_1, rule_2])])).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    assert len(matching) == 1
    assert matching[0].vals[0] == 31
    assert matching[0].vals[1] == 3

def test_tracer():
    rule = Rule(id='r1',
                when=Fact(of_type=C1, var='c1', matches=lambda ctx, this: this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    trace_file_path = "target/unit-trace.ndjson"
    os.makedirs(os.path.dirname(trace_file_path), exist_ok=True)
    if os.path.exists(trace_file_path):
        try:
            os.remove(trace_file_path)
        except OSError:
            raise AssertionError("Intentional test failure")
    try:
        provider = TracerProvider(resource=Resource.create({"service.name": 'knowledgenet unit test'}))
        exporter = FileSpanExporter(trace_file_path)
        # exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        Service(Repository('repo1',[Ruleset('rs1', [rule])])).execute(facts, trc_option='full')
    finally:
        # Make sure that the trace is full written out
        trace.get_tracer_provider().shutdown()

        assert os.path.exists(trace_file_path)
        with io.open(trace_file_path, 'r', encoding='utf-8') as fh:
            entries = [json.loads(line) for line in fh if line.strip()]
        assert len(entries) > 1