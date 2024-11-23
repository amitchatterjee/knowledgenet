######################################
# Rule definition syntactic sugar
######################################
def forClass(cls):
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

######################################
# Functions used in then statements
######################################
def insert(ctx, fact):
    ctx._changes.append((fact, 'insert'))

def update(ctx, fact):
    ctx._changes.append((fact, 'update'))

def delete(ctx, fact):
    ctx._changes.append((fact, 'delete'))
    