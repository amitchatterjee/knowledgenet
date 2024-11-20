
def assign(ctx, **kwargs):
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def insert(ctx, fact):
    # TODO this will need lot more work
    ctx._changes.append((fact, 'insert'))
    