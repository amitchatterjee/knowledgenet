import pytest

import knowledgenet.core.session as session_mod
from knowledgenet.core.session import _resolve_backend
from knowledgenet.rule import Rule, Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert
from knowledgenet.service import Service

from test_helpers.unit_util import find_result_of_type
from test_helpers.unit_facts import C1, R1


def test_resolve_backend_pure_is_always_pure():
    assert _resolve_backend('pure') == 'pure'


def test_resolve_backend_native_requires_availability(monkeypatch):
    monkeypatch.setattr(session_mod, '_NATIVE_AVAILABLE', False)
    with pytest.raises(RuntimeError):
        _resolve_backend('native')


def test_resolve_backend_auto_falls_back_when_native_unavailable(monkeypatch):
    monkeypatch.setattr(session_mod, '_NATIVE_AVAILABLE', False)
    assert _resolve_backend('auto') == 'pure'


def test_resolve_backend_auto_prefers_native_when_available(monkeypatch):
    monkeypatch.setattr(session_mod, '_NATIVE_AVAILABLE', True)
    assert _resolve_backend('auto') == 'native'


def _run_one_rule(backend):
    rule = Rule(id='r1',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this) and this.val > 1),
                then=lambda ctx: insert(ctx, R1(ctx.c1)))
    facts = [C1(1), C1(2)]
    result_facts = Service(Repository('repo1', [Ruleset('rs1', [rule])]), backend=backend).execute(facts)
    return find_result_of_type(R1, result_facts)


@pytest.mark.parametrize('backend', ['auto', 'pure'])
def test_service_execute_unaffected_by_backend_choice(backend):
    matching = _run_one_rule(backend)
    assert len(matching) == 1
    assert len(matching[0].vals) == 1


@pytest.mark.skipif(not session_mod._NATIVE_AVAILABLE, reason="knowledgenet._native not built in this environment")
def test_service_execute_with_native_backend_forced():
    matching = _run_one_rule('native')
    assert len(matching) == 1
    assert len(matching[0].vals) == 1
