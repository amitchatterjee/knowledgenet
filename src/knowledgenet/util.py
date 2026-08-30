"""General-purpose utility helpers shared across Knowledgenet modules."""

from typing import List, Any

def to_tuple(obj):
    """Convert a scalar or iterable value into a tuple.

    Scalars become single-item tuples.
    """
    return obj if isinstance(obj, tuple) else tuple(obj) if isinstance(obj, (list, set, frozenset)) else (obj,)

def to_list(obj):
    """Convert a scalar or iterable value into a list.

    Scalars become single-item lists.
    """
    return obj if isinstance(obj, list) else list(obj) if isinstance(obj, (tuple, set, frozenset)) else [obj]

def to_frozenset(obj):
    """Convert a scalar or iterable value into a frozenset."""
    return obj if isinstance(obj, frozenset) else frozenset(obj) if isinstance(obj, (list, tuple, set)) else frozenset([obj])

def of_type(fact):
    """Return the effective type for a fact.

    Wrapper facts expose their logical ``of_type`` instead of concrete Wrapper
    class to support named/typed matching semantics.
    """
    from knowledgenet.ftypes import Wrapper
    return type(fact) if type(fact) != Wrapper else fact.of_type

def merge(d1: dict[str,Any], d2: dict[str,Any]) -> dict[str,Any]:
    """Recursively merge two dictionaries, preferring right-hand values.

    Nested dict values are merged recursively, list values are merged by index,
    and scalar conflicts are resolved in favor of ``d2``.
    """
    result = {}
    for key in set(d1.keys()) | set(d2.keys()):
        if key not in d1:
            result[key] = d2[key]
        elif key not in d2:
            result[key] = d1[key]
        elif isinstance(d1[key], dict) and isinstance(d2[key], dict):
            result[key] = merge(d1[key], d2[key])
        elif isinstance(d1[key], list) and isinstance(d2[key], list):
            result[key] = d1[key][:len(d1[key])]
            for i in range(len(d2[key])):
                if i < len(d1[key]):
                    if isinstance(d1[key][i], dict) and isinstance(d2[key][i], dict):
                        result[key][i] = merge(d1[key][i], d2[key][i])
                    else:
                        result[key][i] = d2[key][i]
                else:
                    result[key].append(d2[key][i])
        else:
            result[key] = d2[key]
    return result