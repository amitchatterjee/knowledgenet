import pytest
from knowledgenet.shaper import shape

def test_simple_flat_structure():
    properties = {
        "name": "John",
        "age": "30"
    }
    expected = {
        "name": "John",
        "age": "30"
    }
    assert shape(properties) == expected

def test_nested_structure():
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

def test_list_indices():
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

def test_nested_lists():
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

def test_sparse_list():
    properties = {
        "items[0]": "first",
        "items[2]": "third"
    }
    expected = {
        "items": ["first", None, "third"]
    }
    assert shape(properties) == expected

def test_dict_with_lists():
    properties = {
        "data.numbers[0]": "1",
        "data.numbers[1]": "2",
        "data.letters[0]": "a",
        "data.letters[1]": "b",
        "data.name": "test"
    }
    expected = {
        "data": {
            "numbers": ["1", "2"],
            "letters": ["a", "b"],
            "name": "test"
        }
    }
    assert shape(properties) == expected
