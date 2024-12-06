from ftypes import Switch

def insert(ctx, fact):
    ctx._changes.append((fact, 'insert'))

def update(ctx, fact):
    ctx._changes.append((fact, 'update'))

def delete(ctx, fact):
    ctx._changes.append((fact, 'delete'))

def next_ruleset(ctx):
    ctx._changes.append((True, 'break'))

def end(ctx):
    ctx._changes.append((Switch('_end'), 'switch'))

def switch(ctx, ruleset):
    ctx._changes.append((Switch(ruleset), 'switch'))