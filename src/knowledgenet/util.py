def to_tuple(obj):
    return obj if isinstance(obj, tuple) else tuple(obj) if isinstance(obj, (list, set, frozenset)) else (obj,)

def to_list(obj):
    return obj if isinstance(obj, list) else list(obj) if isinstance(obj, (tuple, set, frozenset)) else [obj]

def to_frozenset(obj):
    return obj if isinstance(obj, frozenset) else frozenset(obj) if isinstance(obj, (list, tuple, set)) else frozenset([obj])

def of_type(fact):
    from knowledgenet.ftypes import Wrapper
    return type(fact) if type(fact) != Wrapper else fact.of_type

