def forClass(cls):
    return cls

def expression(exp):
    return exp

def Then(exp):
    return exp

def assign(ctx, **kwargs):
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def insert(ctx, fact):
    ctx._changes.append((fact, 'insert'))
    