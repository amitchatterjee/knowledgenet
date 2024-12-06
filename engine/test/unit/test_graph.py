from graph import Graph

def test_insert():
    comparator = lambda o1, o2: o1 - o2
    g = Graph(comparator)
    # Add first element to an empty
    g.add(1)
    # Append at the end of the list
    g.add(10)
    # Insert between two elements
    g.add(5)
    # Insert at beginning
    g.add(0)
    result = g.to_list()
    assert 4 == len(result)
    assert [0,1,5,10] == result
    
def test_delete():
    comparator = lambda o1, o2: o1 - o2
    g = Graph(comparator)
    for i in range(0,10):
        g.add(i)

    # Delete the first element
    g.delete(0)
    # Delete the last element
    g.delete(9)
    # Delete an element in the middle
    g.delete(5)
    result = g.to_list()
    assert 7 == len(result)
    assert [1,2,3,4,6,7,8] == result

    # Delete the remaining
    for each in result:
        g.delete(each)
    result = g.to_list()
    assert 0 == len(result)

def test_delete_with_next():
    comparator = lambda o1, o2: o1 > o2
    g = Graph(comparator)
    for i in range(0,10):
        g.add(i)
    result = []
    g.new_cursor()
    for i in range(0,5):
        obj = g.next()
        if obj is None:
            break
        result.append(obj)
    assert 5 == len(result)
    assert [0,1,2,3,4] == result
    # The iterator is now pointing to 5
    g.delete(5)
    # Verify that the iterator has moved to the next element
    obj = g.next()
    assert obj is not None
    assert 6 == obj

    # Delete the remaining elements to the right
    for i in range(6,10):
        g.delete(i)
    # The iterator should be null as we deleted the 5 elements to the right
    assert g.next() is None

    # Verify size and content
    assert [0,1,2,3,4]== g.to_list()

def test_return_and_start():
    comparator = lambda o1, o2: o1 - o2
    g = Graph(comparator)
    saved_node = None
    for i in range(0,10):
        # Reverse the insertion order, but it should still get ordered correctly
        node = g.add(9-i)
        if i == 5:
            # Save the middle node
            saved_node = node
    result = g.to_list(element=saved_node)
    # Needs to work out with pen and paper to see if this works :-)
    assert 6 == len(result)
    assert [4, 5, 6, 7, 8, 9] == result

    deleted, saved_node = g.delete(5)
    assert deleted
    result = g.to_list(element=saved_node)
    assert 4 == len(result)
    assert [6, 7, 8, 9] == result

    deleted, saved_node = g.delete(9)
    assert deleted
    assert saved_node is None

def test_ordinal():
    comparator = lambda o1, o2: o1 - o2
    g = Graph(comparator)
    for i in range(0,10):
        node = g.add(i)

    # Move the cursor forward by 5 steps
    g.new_cursor()
    for i in range(0,5):
        obj = g.next()
        assert i == obj

    # Delete an object left of the cursor
    deleted, node = g.delete(2)
    assert deleted
    # Verify that cursor is right of the deleted node 
    assert g.cursor_is_right_of(node)

    # Delete the node where the cursor is set and verify that the cursor is moved to the next position
    deleted, node = g.delete(5)
    assert g.cursor_is_on(node)
    
    # insert an element right of the cursor
    node = g.add(10)
    assert g.cursor_is_left_of(node)

    # insert an element left of the cursor
    node = g.add(-1)
    assert g.cursor_is_right_of(node)

def test_non_default_cursor():
    comparator = lambda o1, o2: o1 - o2
    g = Graph(comparator)
    for i in range(0,10):
        g.add(i)
    # Get a default cursor and iterate through 5 items
    g.new_cursor()
    for i in range(0,5):
        obj = g.next()
        assert i == obj
    # Get a default cursor and iterate through 5 items
    g.new_cursor(cursor_name='x')
    for i in range(0,5):
        obj = g.next('x')
        assert i == obj
    # Make sure that the cursors are still in the same place
    assert 5 == g.next()
    assert 6 == g.next()
    assert 5 == g.next('x')
    assert 6 == g.next('x')
    assert 7 == g.next('x')
    g.delete(7)
    assert 8 == g.next()
    assert 8 == g.next('x')

    
    