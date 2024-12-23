from types import SimpleNamespace
def assign(ctx: SimpleNamespace, **kwargs)->True:
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def global_ctx(ctx:SimpleNamespace)->object:
    return ctx._global

def factset(ctx:SimpleNamespace)->set:
    return ctx._facts
