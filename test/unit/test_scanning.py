
import sys

from knowledgenet.scanner import load_rules_from_filepaths, lookup
from knowledgenet.service import Service

from test_helpers.unit_facts import C1, R1
from test_helpers.unit_util import find_result_of_type
import pytest

@pytest.fixture(scope="module", autouse=True)
def setup():
    load_rules_from_filepaths('test/unit/scanner-rules/repo1/rs1', 'test/unit/scanner-rules/repo1/override', 'test/unit/scanner-rules/repo2/rs10')

def test_rule_loading_default():
    repository = lookup('repo1')
    assert 'repo1' == repository.id
    assert 1 == len(repository.rulesets)
    assert 'rs1' == repository.rulesets[0].id
    assert 2 == len(repository.rulesets[0].rules)
    rules = list(repository.rulesets[0].rules)
    rules.sort(key=lambda e: e.id)
    assert 'rule1' == repository.rulesets[0].rules[0].id
    assert 'rule2' == repository.rulesets[0].rules[1].id

def test_rule_loading_override():
    repository=lookup('repo-override')
    assert 'repo-override' == repository.id
    assert 1 == len(repository.rulesets)
    assert 'ruleset-override' == repository.rulesets[0].id
    assert 'rule-override' == repository.rulesets[0].rules[0].id

def test_lookup_from_multiple_repos():
    with pytest.raises(Exception):
        # An id must be provided
        lookup(['repo1', 'repo2'])
    repository = lookup(['repo1', 'repo2'], id='composite')
    assert 'composite' == repository.id
    assert 2 == len(repository.rulesets)
    assert 'rs1' == repository.rulesets[0].id
    assert 'rs10' == repository.rulesets[1].id

def test_scanning_from_filepath():
    repository = lookup('repo1')
    facts = [C1(5), C1(15)]
    result_facts = Service(repository).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    # Sort by the description. possible descriptions are [small, large] - see the rules
    matching.sort(key=lambda e: e.vals[1])
    assert 2==len(matching)
    assert facts[1] == matching[0].vals[0]
    assert 'large' == matching[0].vals[1]
    assert facts[0] == matching[1].vals[0]
    assert 'small' == matching[1].vals[1]

def test_non_existent_repo():
    with pytest.raises(Exception):
        lookup('norepo')
