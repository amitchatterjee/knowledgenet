import uuid

import pytest

import knowledgenet.core.graph as graph_mod
from knowledgenet.core.graph import Graph

BACKENDS = [
    'pure',
    pytest.param('native', marks=pytest.mark.skipif(
        not graph_mod._NATIVE_AVAILABLE, reason="knowledgenet._native not built in this environment")),
]

@pytest.mark.parametrize('backend', BACKENDS)
def test_insert(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    # Add first element to an empty
    g.add(1,1)
    # Append at the end of the list
    g.add(10,10)
    # Insert between two elements
    g.add(5,5)
    # Insert at beginning
    g.add(0,0)
    result = g.to_list()
    assert len(result) == 4
    assert result == [0,1,5,10]

@pytest.mark.parametrize('backend', BACKENDS)
def test_delete(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    for i in range(0,10):
        g.add(i,i)

    # Delete the first element
    g.delete(0)
    # Delete the last element
    g.delete(9)
    # Delete an element in the middle
    g.delete(5)
    result = g.to_list()
    assert len(result) == 7
    assert result == [1,2,3,4,6,7,8]

    # Delete the remaining
    for each in result:
        g.delete(each)
    result = g.to_list()
    assert len(result) == 0

@pytest.mark.parametrize('backend', BACKENDS)
def test_delete_with_next(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    for i in range(0,10):
        g.add(i,i)
    result = []
    g.new_cursor()
    for i in range(0,5):
        obj = g.next()
        if obj is None:
            break
        result.append(obj)
    assert len(result) == 5
    assert result == [0,1,2,3,4]
    # The iterator is now pointing to 5
    g.delete(5)
    # Verify that the iterator has moved to the next element
    obj = g.next()
    assert obj is not None
    assert obj == 6

    # Delete the remaining elements to the right
    for i in range(6,10):
        g.delete(i)
    # The iterator should be null as we deleted the 5 elements to the right
    assert g.next() is None

    # Verify size and content
    assert g.to_list() == [0,1,2,3,4]

@pytest.mark.parametrize('backend', BACKENDS)
def test_return_and_start(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    saved_node = None
    for i in range(0,10):
        # Reverse the insertion order, but it should still get ordered correctly
        node = g.add(9-i, 9-i)
        if i == 5:
            # Save the middle node
            saved_node = node
    result = g.to_list(element=saved_node)
    # Needs to work out with pen and paper to see if this works :-)
    assert len(result) == 6
    assert result == [4, 5, 6, 7, 8, 9]

    deleted, saved_node = g.delete(5)
    assert deleted
    result = g.to_list(element=saved_node)
    assert len(result) == 4
    assert result == [6, 7, 8, 9]

    deleted, saved_node = g.delete(9)
    assert deleted
    assert saved_node is None

@pytest.mark.parametrize('backend', BACKENDS)
def test_ordinal(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    for i in range(0,10):
        node = g.add(i,i)

    # Move the cursor forward by 5 steps
    g.new_cursor()
    for i in range(0,5):
        obj = g.next()
        assert obj == i

    # Delete an object left of the cursor
    deleted, node = g.delete(2)
    assert deleted
    # Verify that cursor is right of the deleted node
    assert g.cursor_is_right_of(node)

    # Delete the node where the cursor is set and verify that the cursor is moved to the next position
    deleted, node = g.delete(5)
    assert g.cursor_is_on(node)

    # insert an element right of the cursor
    node = g.add(10, 10)
    assert g.cursor_is_left_of(node)

    # insert an element left of the cursor
    node = g.add(-1,-1)
    assert g.cursor_is_right_of(node)

@pytest.mark.parametrize('backend', BACKENDS)
def test_non_default_cursor(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    for i in range(0,10):
        g.add(i,i)
    # Get a default cursor and iterate through 5 items
    g.new_cursor()
    for i in range(0,5):
        obj = g.next()
        assert obj == i
    # Get a default cursor and iterate through 5 items
    g.new_cursor(cursor_name='x')
    for i in range(0,5):
        obj = g.next('x')
        assert obj == i
    # Make sure that the cursors are still in the same place
    assert g.next() == 5
    assert g.next() == 6
    assert g.next('x') == 5
    assert g.next('x') == 6
    assert g.next('x') == 7
    g.delete(7)
    assert g.next() == 8
    assert g.next('x') == 8

@pytest.mark.parametrize('backend', BACKENDS)
def test_many_inserts_in_between(backend):
    '''
    The primary purpose of this test is to make sure that the precision of the graph._ordinal function is good enough for handling high number of facts between two facts
    '''
    g = Graph(str(uuid.uuid4()), backend=backend)
    # Increasing this number slows down the tests. But, I ran with 10000
    high = 100
    g.add(0,0)
    g.add(high,high)
    for i in range(1,high):
        g.add(i,i)
    result = g.to_list()
    assert len(result) == high+1
    for i,j in enumerate(result):
        assert j == i

@pytest.mark.parametrize('backend', BACKENDS)
def test_next_elements(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    g.new_cursor()
    assert len(g.next_elements()) == 0

    for i in range(0, 10):
        g.add(i, i)
        g.add(i, i)

    g.new_cursor()
    for i in range(0, 10):
        result = g.next_elements()
        assert len(result) == 2
        assert [e.ordinal for e in result] == [i, i]

class C:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return str(self.val)
    def __repr__(self):
        return str(self)
        
@pytest.mark.parametrize('backend', BACKENDS)
def test_comparator_based_insert(backend):
    g = Graph(str(uuid.uuid4()), comparator=lambda obj,other: obj.val - other.val, backend=backend)
    g.add(C(1))
    g.add(C(3))
    g.add(C(0))
    g.add(C(2))
    g.add(C(4))
    g.add(C(-1))
    result = g.to_list()
    assert len(result) == 6
    for i in range(0, len(result)):
        assert i-1 == result[i].val

@pytest.mark.parametrize('backend', BACKENDS)
def test_comparator_disregard_ordinal(backend):
    '''Verify that even if we supply an ordinal, it is not used when a comparator is specified'''
    g = Graph(str(uuid.uuid4()), comparator=lambda obj,other: obj.val - other.val, backend=backend)
    g.add(C(1), 9)
    g.add(C(3), 8)
    g.add(C(0), 7)
    g.add(C(2), 6)
    g.add(C(4), 5)
    g.add(C(-1), 4)
    result = g.to_list()
    assert len(result) == 6
    for i in range(0, len(result)):
        assert i-1 == result[i].val

@pytest.mark.parametrize('backend', BACKENDS)
def test_same_ordinal_ties_preserve_insertion_order(backend):
    # Distinct objects (unlike test_next_elements' identical int placeholders)
    # so insertion order is actually distinguishable in the result.
    g = Graph(str(uuid.uuid4()), backend=backend)
    g.add('a', 5)
    g.add('b', 5)
    g.add('c', 5)
    assert g.to_list() == ['a', 'b', 'c']
    # A later, distinct ordinal still lands after the whole tied run
    g.add('d', 5)
    g.add('e', 10)
    assert g.to_list() == ['a', 'b', 'c', 'd', 'e']

@pytest.mark.parametrize('backend', BACKENDS)
def test_same_ordinal_ties_interleaved_with_other_ordinals(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    g.add('a', 1)
    g.add('b', 3)
    g.add('c', 1)   # ties with 'a' at ordinal 1, must land after 'a', before 'b'
    g.add('d', 2)   # new ordinal between the 1-run and the 3-run
    g.add('e', 3)   # ties with 'b' at ordinal 3, must land after 'b'
    assert g.to_list() == ['a', 'c', 'd', 'b', 'e']

@pytest.mark.parametrize('backend', BACKENDS)
def test_delete_tail_of_ordinal_bucket_then_reinsert(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    g.add('a', 5)
    node_b = g.add('b', 5)
    g.delete_element(node_b)  # 'b' was the ordinal-5 bucket's tail
    g.add('c', 5)             # must land after 'a', the new tail
    assert g.to_list() == ['a', 'c']

@pytest.mark.parametrize('backend', BACKENDS)
def test_delete_only_element_of_ordinal_then_insert_neighbor(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    g.add('a', 1)
    node_b = g.add('b', 5)   # ordinal 5's only element
    g.add('c', 10)
    g.delete_element(node_b)  # ordinal-5 bucket must be dropped entirely
    g.add('d', 5)             # re-introducing ordinal 5 must slot between 'a' and 'c' again
    assert g.to_list() == ['a', 'd', 'c']

@pytest.mark.parametrize('backend', BACKENDS)
def test_last_pointer_tracks_tail_through_adds_and_deletes(backend):
    g = Graph(str(uuid.uuid4()), backend=backend)
    assert g.last is None
    node_a = g.add('a', 1)
    assert g.last is node_a
    node_b = g.add('b', 5)
    assert g.last is node_b
    g.add('c', 3)  # inserted in the middle - tail unchanged
    assert g.last is node_b
    g.delete_element(node_b)
    assert g.last is not None and g.last.obj == 'c'
