from knowledgenet.factset import Factset
from knowledgenet.container import Collector
from knowledgenet.ftypes import Wrapper

def test_add_to_factset_with_duplicate_collectors():
    factset = Factset()

    # Two facts with exact same params
    collector1 = Collector(of_type=str, group="group1", name='x')
    collector2 = Collector(of_type=str, group="group1", name='x')

    new_facts, updated_facts = factset.add_facts([collector1, collector2])
    assert 1 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 1 == len(factset.facts)

    new_facts, updated_facts = factset.add_facts([collector1, collector2])
    assert 0 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 1 == len(factset.facts)

    collector3 = Collector(of_type=str, group="group3", name='x')
    new_facts, updated_facts = factset.add_facts([collector3])
    assert 1 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 2 == len(factset.facts)

def test_add_to_factset_with_duplicate_wrapper():
    factset = Factset()

    # Two facts with exact same params
    props = {'id': 'abcd', 'a': 0, 'b': 'b'}
    wrapper1 = Wrapper(of_type=str, name='x', props=props)
    wrapper2 = Wrapper(of_type=str, name='x', props=props)

    new_facts, updated_facts = factset.add_facts([wrapper1, wrapper2])
    assert 1 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 1 == len(factset.facts)

    new_facts, updated_facts = factset.add_facts([wrapper1, wrapper2])
    assert 0 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 1 == len(factset.facts)

    wrapper3 = Wrapper(of_type=str, name='y', props=props)
    new_facts, updated_facts = factset.add_facts([wrapper3])
    assert 1 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 2 == len(factset.facts)

# TODO - more to come