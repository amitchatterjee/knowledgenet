def to_tuple(obj):
    return obj if isinstance(obj, tuple) else (*obj,) if isinstance(obj,list) else (obj,)

def to_list(obj):
    return obj if isinstance(obj, list) else [obj] if isinstance(obj,tuple) else [obj]