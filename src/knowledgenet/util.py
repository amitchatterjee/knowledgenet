from typing import List

def to_tuple(obj):
    return obj if isinstance(obj, tuple) else tuple(obj) if isinstance(obj, (list, set, frozenset)) else (obj,)

def to_list(obj):
    return obj if isinstance(obj, list) else list(obj) if isinstance(obj, (tuple, set, frozenset)) else [obj]

def to_frozenset(obj):
    return obj if isinstance(obj, frozenset) else frozenset(obj) if isinstance(obj, (list, tuple, set)) else frozenset([obj])

def of_type(fact):
    from knowledgenet.ftypes import Wrapper
    return type(fact) if type(fact) != Wrapper else fact.of_type

def merge(d1: dict[str,object], d2: dict[str,object]) -> dict[str,object]:
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