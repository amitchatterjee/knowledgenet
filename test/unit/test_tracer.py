import pytest

import knowledgenet.core.tracer as tracer_mod
from knowledgenet.service import trace_level, trace_details


def _spy_on_normalize_attribute(monkeypatch):
    calls: list = []
    original = tracer_mod.normalize_attribute
    def spy(value, details):
        calls.append(value)
        return original(value, details)
    monkeypatch.setattr(tracer_mod, 'normalize_attribute', spy)
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
