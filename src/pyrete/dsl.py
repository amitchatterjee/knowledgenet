
def assign(ctx, **kwargs):
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def insert(ctx, fact):
    ctx.facts.append(fact)
    # TODO this will need lot more work