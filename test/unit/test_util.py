import pytest
from knowledgenet.util import to_tuple, to_list, to_frozenset, of_type
from knowledgenet.ftypes import Wrapper

def test_to_tuple():
    assert (1, 2, 3) == to_tuple((1, 2, 3))
    assert (1, 2, 3) == to_tuple([1, 2, 3])
    assert (1, 2, 3) == to_tuple({1, 2, 3})
    assert (1, 2, 3) == to_tuple(frozenset([1, 2, 3]))
    assert (1,) == to_tuple(1)

def test_to_list():
    assert [1, 2, 3] == to_list([1, 2, 3])
    assert [1, 2, 3] == to_list((1, 2, 3))
    assert [1, 2, 3] == to_list({1, 2, 3})
    assert [1, 2, 3] == to_list(frozenset([1, 2, 3]))
    assert [1] == to_list(1)

def test_to_frozenset():
    assert frozenset([1, 2, 3]) == to_frozenset(frozenset([1, 2, 3]))
    assert frozenset([1, 2, 3]) == to_frozenset([1, 2, 3])
    assert frozenset([1, 2, 3]) == to_frozenset((1, 2, 3))
    assert frozenset([1, 2, 3]) == to_frozenset({1, 2, 3})
    assert frozenset([1]) == to_frozenset(1)

def test_of_type():
    assert int == of_type(1)
    assert 'int' == of_type(Wrapper(of_type='int'))
    assert int == of_type(Wrapper(of_type=int))