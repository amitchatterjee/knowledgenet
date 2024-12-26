from knowledgenet.ftypes import Switch

def _add_key(ctx, key, fact):
    if key not in ctx._changes:
        ctx._changes[key] = []
    ctx._changes[key].append(fact)

def insert(ctx, fact):
    _add_key(ctx, 'insert', fact)

def update(ctx, fact):
    _add_key(ctx, 'update', fact)

def delete(ctx, fact):
    _add_key(ctx, 'delete', fact)

def next_ruleset(ctx):
    ctx._changes['break'] = True

def switch(ctx, ruleset):
    ctx._changes['switch'] = Switch(ruleset)

def end(ctx):
    switch(ctx, '_end')
