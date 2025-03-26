from knowledgenet.factset import Factset
from knowledgenet.container import Collector
from knowledgenet.ftypes import Wrapper
from test_helpers.unit_facts import C1

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

def test_collector_updates():
    factset = Factset()

    c1 = C1(10)
    c2 = C1(20)
    collector1 = Collector(of_type=C1, group="group1", name='x')

    new_facts, updated_facts = factset.add_facts([collector1, c1, c2])
    assert 3 == len(new_facts)
    assert 0 == len(updated_facts)
    assert 3 == len(factset.facts)
    assert c1 in collector1.collection
    assert c2 in collector1.collection

    updated_facts = factset.update_facts([c1])
    assert 1 == len(updated_facts)
    assert collector1 in updated_facts

    updated_facts = factset.del_facts([c1])
    assert 1 == len(updated_facts)
    assert collector1 in updated_facts
    assert 2 == len(factset.facts)
    assert c1 not in collector1.collection

    new_facts,updated_facts = factset.add_facts([c3:=C1(30)])
    assert 1 == len(new_facts)
    assert 1 == len(updated_facts)
    assert 3 == len(factset.facts)
    assert c2 in collector1.collection
    assert c3 in collector1.collection

# TODO - more to come