import pytest
from knowledgenet.util import merge, to_tuple, to_list, to_frozenset, of_type, shape
from knowledgenet.ftypes import Wrapper

def test_to_tuple():
    assert to_tuple((1, 2, 3)) == (1, 2, 3)
    assert to_tuple([1, 2, 3]) == (1, 2, 3)
    assert to_tuple({1, 2, 3}) == (1, 2, 3)
    assert to_tuple(frozenset([1, 2, 3])) == (1, 2, 3)
    assert to_tuple(1) == (1,)

def test_to_list():
    assert to_list([1, 2, 3]) == [1, 2, 3]
    assert to_list((1, 2, 3)) == [1, 2, 3]
    assert to_list({1, 2, 3}) == [1, 2, 3]
    assert to_list(frozenset([1, 2, 3])) == [1, 2, 3]
    assert to_list(1) == [1]

def test_to_frozenset():
    assert to_frozenset(frozenset([1, 2, 3])) == frozenset([1, 2, 3])
    assert to_frozenset([1, 2, 3]) == frozenset([1, 2, 3])
    assert to_frozenset((1, 2, 3)) == frozenset([1, 2, 3])
    assert to_frozenset({1, 2, 3}) == frozenset([1, 2, 3])
    assert to_frozenset(1) == frozenset([1])

def test_of_type():
    assert of_type(1) == int
    assert of_type(Wrapper(of_type='int')) == 'int'
    assert of_type(Wrapper(of_type=int)) == int


def test_shaper_simple_flat_structure():
    properties = {
        "name": "John",
        "age": "30"
    }
    expected = {
        "name": "John",
        "age": "30"
    }
    assert shape(properties) == expected

def test_shaper_nested_structure():
    properties = {
        "person.name": "John",
        "person.address.street": "Main St",
        "person.address.city": "New York"
    }
    expected = {
        "person": {
            "name": "John",
            "address": {
                "street": "Main St",
                "city": "New York"
            }
        }
    }
    assert shape(properties) == expected

def test_shaper_list_indices():
    properties = {
        "users[0].name": "John",
        "users[1].name": "Jane",
        "users[0].age": "30",
        "users[1].age": "25"
    }
    expected = {
        "users": [
            {"name": "John", "age": "30"},
            {"name": "Jane", "age": "25"}
        ]
    }
    assert shape(properties) == expected

def test_shaper_nested_lists():
    properties = {
        "departments[0].employees[0].name": "John",
        "departments[0].employees[1].name": "Jane",
        "departments[1].employees[0].name": "Bob"
    }
    expected = {
        "departments": [
            {"employees": [
                {"name": "John"},
                {"name": "Jane"}
            ]},
            {"employees": [
                {"name": "Bob"}
            ]}
        ]
    }
    assert shape(properties) == expected

def test_shaper_sparse_list():
    properties = {
        "items[0]": "first",
        "items[2]": "third"
    }
    expected = {
        "items": ["first", None, "third"]
    }
    assert shape(properties) == expected
    
def test_merge_simple_dicts():
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 3, "c": 4}
    expected = {"a": 1, "b": 3, "c": 4}
    assert merge(d1, d2) == expected

def test_merge_nested_dicts():
    d1 = {"person": {"name": "John", "age": 30}}
    d2 = {"person": {"age": 31, "city": "NY"}}
    expected = {"person": {"name": "John", "age": 31, "city": "NY"}}
    assert merge(d1, d2) == expected

def test_merge_lists():
    d1 = {"items": [1, 2, 3]}
    d2 = {"items": [4, 5, 6, 7]}
    expected = {"items": [4, 5, 6, 7]}
    assert merge(d1, d2) == expected

def test_merge_nested_lists():
    d1 = {"users": [{"name": "John"}, {"name": "Jane"}]}
    d2 = {"users": [{"age": 30}, {"age": 25}, {"name": "Bob"}]}
    expected = {"users": [
        {"name": "John", "age": 30},
        {"name": "Jane", "age": 25},
        {"name": "Bob"}
    ]}
    assert merge(d1, d2) == expected

def test_merge_empty_dicts():
    d1 = {}
    d2 = {"a": 1}
    assert merge(d1, d2) == {"a": 1}
    assert merge(d2, d1) == {"a": 1}
