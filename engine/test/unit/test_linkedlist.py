from linkedlist import TraversingLinkedList

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

    result = []
    ll.start()
    while True:
        obj = ll.next()
        if obj is None:
            break
        result.append(obj)
    assert 4 == len(result)
    assert [0,1,5,10] == result