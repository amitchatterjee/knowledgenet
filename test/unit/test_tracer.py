import pytest

import knowledgenet.core.tracer as tracer_mod
from knowledgenet.service import Service, trace_level, trace_details
from knowledgenet.repository import Repository
from knowledgenet.ruleset import Ruleset
from knowledgenet.rule import Fact, Rule
from knowledgenet.helper import assign
from knowledgenet.controls import insert

from test_helpers.unit_facts import C1, R1


def _spy_on_normalize_attribute(monkeypatch):
    calls: list = []
    original = tracer_mod.normalize_attribute
    def spy(value, details):
        calls.append(value)
        return original(value, details)
    monkeypatch.setattr(tracer_mod, 'normalize_attribute', spy)
    return calls


def _spy_on_trace_context_factory(monkeypatch):
    calls: list = []
    original = tracer_mod.trace_context_factory
    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(tracer_mod, 'trace_context_factory', spy)
    return calls


def _set_trace_vars(level: int, details: int = 0):
    level_token = trace_level.set(level)
    details_token = trace_details.set(details)
    return level_token, details_token


def _reset_trace_vars(tokens) -> None:
    level_token, details_token = tokens
    trace_level.reset(level_token)
    trace_details.reset(details_token)


def test_trace_returns_function_result_when_disabled():
    @tracer_mod.trace(level=5)
    def f(x):
        return x * 2

    tokens = _set_trace_vars(level=0)
    try:
        assert f(21) == 42
    finally:
        _reset_trace_vars(tokens)

def test_trace_returns_function_result_when_enabled():
    @tracer_mod.trace(level=1)
    def f(x):
        return x * 2

    tokens = _set_trace_vars(level=5)
    try:
        assert f(21) == 42
    finally:
        _reset_trace_vars(tokens)

def test_trace_disabled_skips_normalize_attribute(monkeypatch):
    calls = _spy_on_normalize_attribute(monkeypatch)

    @tracer_mod.trace(level=5)
    def f(x):
        return x * 2

    tokens = _set_trace_vars(level=0)  # below the decorator's level
    try:
        f(21)
    finally:
        _reset_trace_vars(tokens)

    assert calls == []

def test_trace_enabled_calls_normalize_attribute_for_args_and_return(monkeypatch):
    calls = _spy_on_normalize_attribute(monkeypatch)

    @tracer_mod.trace(level=1)
    def f(x):
        return x * 2

    tokens = _set_trace_vars(level=5)
    try:
        f(21)
    finally:
        _reset_trace_vars(tokens)

    assert 21 in calls
    assert 42 in calls

def test_trace_disabled_never_calls_trace_context_factory(monkeypatch):
    # Proves the fast-path short-circuit itself, not just its externally
    # observable effects (already covered by the disabled-path tests above).
    calls = _spy_on_trace_context_factory(monkeypatch)

    @tracer_mod.trace(level=5)
    def f(x):
        return x * 2

    tokens = _set_trace_vars(level=0)  # below the decorator's level
    try:
        assert f(21) == 42
    finally:
        _reset_trace_vars(tokens)

    assert calls == []

def test_trace_filter_suppresses_tracing_even_when_level_matches(monkeypatch):
    calls = _spy_on_normalize_attribute(monkeypatch)

    @tracer_mod.trace(level=1, filter=lambda args, kwargs: False)
    def f(x):
        return x

    tokens = _set_trace_vars(level=5)
    try:
        f(10)
    finally:
        _reset_trace_vars(tokens)

    assert calls == []

def test_trace_propagates_exceptions():
    @tracer_mod.trace()
    def boom():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        boom()

def test_trace_bare_decorator_without_parens():
    @tracer_mod.trace
    def f(x):
        return x + 1

    assert f(1) == 2

def test_trace_summary_attr_captures_named_attribute_when_enabled(monkeypatch):
    calls = _spy_on_normalize_attribute(monkeypatch)

    class Obj:
        def __init__(self):
            self.summary: list | None = None

        @tracer_mod.trace(level=1, summary_attr='summary')
        def run(self):
            self.summary = ['a', 'b']
            return True

    tokens = _set_trace_vars(level=5)
    try:
        Obj().run()
    finally:
        _reset_trace_vars(tokens)

    assert ['a', 'b'] in calls

def test_trace_summary_attr_skipped_when_disabled(monkeypatch):
    calls = _spy_on_normalize_attribute(monkeypatch)

    class Obj:
        def __init__(self):
            self.summary: list | None = None

        @tracer_mod.trace(level=5, summary_attr='summary')
        def run(self):
            self.summary = ['a', 'b']
            return True

    tokens = _set_trace_vars(level=0)
    try:
        Obj().run()
    finally:
        _reset_trace_vars(tokens)

    assert calls == []

def test_trace_summary_attr_accepts_a_tuple_of_names(monkeypatch):
    calls = _spy_on_normalize_attribute(monkeypatch)

    class Obj:
        def __init__(self):
            self.a: int | None = None
            self.b: int | None = None

        @tracer_mod.trace(level=1, summary_attr=('a', 'b'))
        def run(self):
            self.a, self.b = 1, 2
            return True

    tokens = _set_trace_vars(level=5)
    try:
        Obj().run()
    finally:
        _reset_trace_vars(tokens)

    assert 1 in calls
    assert 2 in calls

def test_node_execute_traced_with_leaf_summary_when_then_not_traced(monkeypatch):
    spans: list = []

    class _FakeSpan:
        def __init__(self, name, attributes):
            self.name = name
            self.attributes = dict(attributes or {})
        def __enter__(self):
            spans.append(self)
            return self
        def set_attribute(self, key, val):
            self.attributes[key] = val
        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    monkeypatch.setattr(tracer_mod.otel_tracer, 'start_as_current_span',
                         lambda name, *a, **kw: _FakeSpan(name, kw.get('attributes')))

    rule = Rule(id='r1',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    Service(Repository('repo1', [Ruleset('rs1', [rule])])).execute(facts, trc_level=1)

    assert not any(s.name.endswith('.Leaf.execute') for s in spans)
    assert not any(s.name.endswith('.Node._execute_thens') for s in spans)

    fired = [s for s in spans if s.name.endswith('.Node.execute') and s.attributes.get('return') is True]
    assert fired, spans
    assert any(s.attributes.get('leaf_results') for s in fired)
    # leaf_results carries (leaf_id, result, duration) tuples, stringified -
    # confirm a numeric-looking duration is actually present, not just the id.
    assert any('True' in str(s.attributes.get('leaf_results')) for s in fired)
    assert any(s.attributes.get('then_duration') is not None for s in fired)

def test_normalize_attribute_primitive_passthrough():
    assert tracer_mod.normalize_attribute(5, 0) == 5
    assert tracer_mod.normalize_attribute(5.5, 0) == 5.5
    assert tracer_mod.normalize_attribute(True, 0) is True
    assert tracer_mod.normalize_attribute('short', 0) == 'short'

def test_normalize_attribute_truncates_long_stringified_objects():
    class Obj:
        def __str__(self):
            return 'x' * 500

    result = tracer_mod.normalize_attribute(Obj(), 0)
    max_size = tracer_mod.trace_details_to_max_size(0)
    assert result == 'x' * max_size + '...'
