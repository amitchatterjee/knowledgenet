
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
    assert repository.id == 'repo1'
    assert repository.rulesets[0].id == 'rs1'
    assert len(repository.rulesets) == 1
    assert len(repository.rulesets[0].rules) == 2
    rules = list(repository.rulesets[0].rules)
    rules.sort(key=lambda e: e.id)
    assert repository.rulesets[0].rules[0].id == 'rule1'
    assert repository.rulesets[0].rules[1].id == 'rule2'

def test_rule_loading_override():
    repository=lookup('repo-override')
    assert repository.id == 'repo-override'
    assert len(repository.rulesets) == 1
    assert repository.rulesets[0].id == 'ruleset-override'
    assert repository.rulesets[0].rules[0].id == 'rule-override'

def test_lookup_from_multiple_repos():
    with pytest.raises(Exception):
        # An id must be provided
        lookup(['repo1', 'repo2'])
    repository = lookup(['repo1', 'repo2'], id='composite')
    assert repository.id == 'composite'
    assert len(repository.rulesets) == 2
    assert repository.rulesets[0].id == 'rs1'
    assert repository.rulesets[1].id == 'rs10'

def test_scanning_from_filepath():
    repository = lookup('repo1')
    facts = [C1(5), C1(15)]
    result_facts = Service(repository).execute(facts)
    matching = find_result_of_type(R1, result_facts)
    # Sort by the description. possible descriptions are [small, large] - see the rules
    matching.sort(key=lambda e: e.vals[1])
    assert len(matching) == 2
    assert matching[0].vals[0] == facts[1]
    assert matching[0].vals[1] == 'large'
    assert matching[1].vals[0] == facts[0]
    assert matching[1].vals[1] == 'small'

def test_non_existent_repo():
    with pytest.raises(Exception):
        lookup('norepo')
