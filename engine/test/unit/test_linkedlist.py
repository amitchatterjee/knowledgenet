from linkedlist import TraversingLinkedList

def get_list(ll, node=None):
    result = []
    ll.start(node)
    while True:
        obj = ll.next()
        if obj is None:
            break
        result.append(obj)
    return result

def test_insert():
    comparator = lambda o1, o2: o1 - o2
    ll = TraversingLinkedList(comparator)
    # Add first element to an empty
    ll.insert(1)
    # Append at the end of the list
    ll.insert(10)
    # Insert between two elements
    ll.insert(5)
    # Insert at beginning
    ll.insert(0)
    result = get_list(ll)
    assert 4 == len(result)
    assert [0,1,5,10] == result
    
def test_delete():
    comparator = lambda o1, o2: o1 - o2
    ll = TraversingLinkedList(comparator)
    for i in range(0,10):
        ll.insert(i)

    # Delete the first element
    ll.delete(0)
    # Delete the last element
    ll.delete(9)
    # Delete an element in the middle
    ll.delete(5)
    result = get_list(ll)
    assert 7 == len(result)
    assert [1,2,3,4,6,7,8] == result

    # Delete the remaining
    for each in result:
        ll.delete(each)
    result = get_list(ll)
    assert 0 == len(result)

def test_delete_with_next():
    comparator = lambda o1, o2: o1 > o2
    ll = TraversingLinkedList(comparator)
    for i in range(0,10):
        ll.insert(i)
    result = []
    ll.start()
    for i in range(0,5):
        obj = ll.next()
        if obj is None:
            break
        result.append(obj)
    assert 5 == len(result)
    assert [0,1,2,3,4] == result
    # The iterator is now pointing to 5
    ll.delete(5)
    # Verify that the iterator has moved to the next element
    obj = ll.next()
    assert obj is not None
    assert 6 == obj

    # Delete the remaining elements to the right
    for i in range(6,10):
        ll.delete(i)
    # The iterator should be null as we deleted the 5 elements to the right
    assert ll.next() is None

    # Verify size and content
    assert [0,1,2,3,4]== get_list(ll)

def test_return_and_start():
    comparator = lambda o1, o2: o1 - o2
    ll = TraversingLinkedList(comparator)
    saved_node = None
    for i in range(0,10):
        # Reverse the insertion order, but it should still get ordered correctly
        node = ll.insert(9-i)
        if i == 5:
            # Save the middle node
            saved_node = node
    result = get_list(ll, saved_node)
    # Needs to work out with pen and paper to see if this works :-)
    assert 6 == len(result)
    assert [4, 5, 6, 7, 8, 9] == result

    saved_node = ll.delete(5)
    result = get_list(ll, saved_node)
    assert 4 == len(result)
    assert [6, 7, 8, 9] == result

    saved_node = ll.delete(9)
    assert saved_node is None

def test_ordinal():
    comparator = lambda o1, o2: o1 - o2
    ll = TraversingLinkedList(comparator)
    for i in range(0,10):
        node = ll.insert(i)

    # Move the pointer forward by 5 steps
    ll.start()
    for i in range(0,5):
        obj = ll.next()
        assert i == obj

    # Delete an object left of the current pointer
    node = ll.delete(2)
    # Verify that current pointer is right of the deleted node 
    assert ll.is_right_of(node)

    # Now delete the node where the current pointer is set and verify that the current pointer is moved to the next position
    node = ll.delete(5)
    assert ll.is_on_node(node)
    
    # insert an element right of the current pointer
    node = ll.insert(10)
    assert ll.is_left_of(node)

    # insert an element left of the current pointer
    node = ll.insert(-1)
    assert ll.is_right_of(node)