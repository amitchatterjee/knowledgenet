import pytest
from knowledgenet.factset import Factset
from knowledgenet.container import Collector


def test_add_facts_with_duplicate_collectors():
    factset = Factset()

    # Two facts with exact same params
    collector1 = Collector(of_type=str, group="group1", name='x')
    collector2 = Collector(of_type=str, group="group1", name='x')

    new_facts, updated_facts = factset.add_facts([collector1, collector2])
    assert 1 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 1 == len(factset.facts)

    assert 1 == len(factset._type_to_collectors[str])
    assert collector1 in factset._type_to_collectors[str]
    
    assert 1 == len(factset._group_to_collectors["group1"])
    assert collector1 in factset._group_to_collectors["group1"]
