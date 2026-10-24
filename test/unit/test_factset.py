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
    assert len(new_facts) == 1
    assert len(updated_facts) == 0
    assert len(factset.facts) == 1

    new_facts, updated_facts = factset.add_facts([collector1, collector2])
    assert len(new_facts) == 0
    assert len(updated_facts) == 0
    assert len(factset.facts) == 1

    collector3 = Collector(of_type=str, group="group3", name='x')
    new_facts, updated_facts = factset.add_facts([collector3])
    assert len(new_facts) == 1
    assert len(updated_facts) == 0
    assert len(factset.facts) == 2

def test_add_to_factset_with_duplicate_wrapper():
    factset = Factset()

    # Two facts with exact same params
    props = {'id': 'abcd', 'a': 0, 'b': 'b'}
    wrapper1 = Wrapper(of_type=str, name='x', props=props)
    wrapper2 = Wrapper(of_type=str, name='x', props=props)

    new_facts, updated_facts = factset.add_facts([wrapper1, wrapper2])
    assert len(new_facts) == 1
    assert len(updated_facts) == 0
    assert len(factset.facts) == 1

    new_facts, updated_facts = factset.add_facts([wrapper1, wrapper2])
    assert len(new_facts) == 0
    assert len(updated_facts) == 0
    assert len(factset.facts) == 1

    wrapper3 = Wrapper(of_type=str, name='y', props=props)
    new_facts, updated_facts = factset.add_facts([wrapper3])
    assert len(new_facts) == 1
    assert len(updated_facts) == 0
    assert len(factset.facts) == 2

def test_collector_updates():
    factset = Factset()

    c1 = C1(10)
    c2 = C1(20)
    collector1 = Collector(of_type=C1, group="group1", name='x')

    new_facts, updated_facts = factset.add_facts([collector1, c1, c2])
    assert len(new_facts) == 3
    assert len(updated_facts) == 0
    assert len(factset.facts) == 3
    assert c1 in collector1.collection
    assert c2 in collector1.collection

    updated_facts = factset.update_facts([c1])
    assert len(updated_facts) == 1
    assert collector1 in updated_facts

    updated_facts = factset.del_facts([c1])
    assert len(updated_facts) == 1
    assert collector1 in updated_facts
    assert len(factset.facts) == 2
    assert c1 not in collector1.collection

    new_facts,updated_facts = factset.add_facts([c3:=C1(30)])
    assert len(new_facts) == 1
    assert len(updated_facts) == 1
    assert len(factset.facts) == 3
    assert c2 in collector1.collection
    assert c3 in collector1.collection

def test_find_returns_a_copy_safe_to_mutate():
    factset = Factset()
    c1 = C1(10)
    factset.add_facts([c1])

    result = factset.find(of_type=C1)
    assert result == {c1}
    result.add(C1(20))  # mutating the result must not affect the factset
    assert factset.find(of_type=C1) == {c1}

def test_population_returns_the_live_index_set():
    # _population() is the internal fast path Session's hot loop uses instead
    # of find() - it must skip find()'s copy, returning the actual index set.
    factset = Factset()
    c1 = C1(10)
    factset.add_facts([c1])

    assert factset._population(C1) is factset._type_to_facts[C1]
    assert factset._population(C1) == {c1}

    collector = Collector(of_type=C1, group='group1', name='x')
    factset.add_facts([collector])
    assert factset._population(Collector, 'group1') is factset._group_to_collectors['group1']

# TODO - more to come