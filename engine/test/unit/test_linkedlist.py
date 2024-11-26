from linkedlist import TraversingLinkedList

def get_list(ll):
    result = []
    ll.start()
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
    assert 4 == ll.size()

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
    assert 0 == ll.size()

def test_delete_with_next():
    comparator = lambda o1, o2: o1 - o2
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
    # Check if the obj_lookup looks good
    obj_lookup = [e[2] for e in ll.obj_lookup.values()]
    obj_lookup.sort()
    assert [0,1,2,3,4] == obj_lookup

    # Verify size and content
    assert 5 == ll.size()
    assert obj_lookup == get_list(ll)