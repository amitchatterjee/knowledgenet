
from scanner import load_rules
from knowledge_registry import lookup
from service import execute

from test_helpers.test_facts import C1, R1
from test_helpers.test_util import find_result_of_type

def test_scanning():
    load_rules('test/unit/scanner_rules')
    knowledge = lookup('k1')
    facts = [C1(5), C1(15)]
    result_facts = execute(knowledge,facts)
    matching = find_result_of_type(R1, result_facts)
    # Sort by the description. possible descriptions are [small, large] - see the rules
    matching.sort(key=lambda e: e.vals[1])
    assert 2==len(matching)
    print(matching[0])
    assert facts[1] == matching[0].vals[0]
    assert 'large' == matching[0].vals[1]
    assert facts[0] == matching[1].vals[0]
    assert 'small' == matching[1].vals[1]
