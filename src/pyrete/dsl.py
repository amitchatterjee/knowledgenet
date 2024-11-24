######################################
# Rule definition syntactic sugar
######################################
def forType(cls):
    return cls

def expression(exp):
    return exp

def Then(exp):
    return exp

######################################
# Functions used in when statements
######################################
def assign(ctx, **kwargs):
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True
