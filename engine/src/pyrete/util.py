def to_tuple(obj):
    return obj if isinstance(obj, tuple) else (*obj,) if isinstance(obj,list) else (obj,)