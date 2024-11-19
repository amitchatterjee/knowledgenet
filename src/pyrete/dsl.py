
def assign(facts, **kwargs):
    for key, value in kwargs.items():
        setattr(facts, key, value)
    return True