def assign(ctx, **kwargs):
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def global_ctx(ctx):
    return ctx._global

def factset(ctx):
    return ctx._facts
