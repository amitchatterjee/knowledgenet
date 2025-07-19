import uuid
from knowledgenet.core.graph import Graph

def test_insert():
    g = Graph(str(uuid.uuid4()))
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
    
def test_delete():
    g = Graph(str(uuid.uuid4()))
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

def test_delete_with_next():
    g = Graph(str(uuid.uuid4()))
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

def test_return_and_start():
    g = Graph(str(uuid.uuid4()))
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

def test_ordinal():
    g = Graph(str(uuid.uuid4()))
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

def test_non_default_cursor():
    g = Graph(str(uuid.uuid4()))
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

def test_many_inserts_in_between():
    '''
    The primary purpose of this test is to make sure that the precision of the graph._ordinal function is good enough for handling high number of facts between two facts
    '''
    g = Graph(str(uuid.uuid4()))
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

def test_next_elements():
    g = Graph(str(uuid.uuid4()))
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
