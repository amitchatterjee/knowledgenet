def insert(ctx, fact):
    ctx._changes.append((fact, 'insert'))

def update(ctx, fact):
    ctx._changes.append((fact, 'update'))

def delete(ctx, fact):
    ctx._changes.append((fact, 'delete'))