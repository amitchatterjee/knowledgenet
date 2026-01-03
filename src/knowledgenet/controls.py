from knowledgenet.core.tracer import trace
from knowledgenet.ftypes import Switch

def _add_key(ctx, key, fact):
    if key not in ctx._changes:
        ctx._changes[key] = []
    ctx._changes[key].append(fact)

@trace(level=3)
def insert(ctx, fact):
    _add_key(ctx, 'insert', fact)

@trace(level=3)
def update(ctx, fact):
    _add_key(ctx, 'update', fact)

@trace(level=3)
def delete(ctx, fact):
    _add_key(ctx, 'delete', fact)

@trace(level=3)
def next_ruleset(ctx):
    ctx._changes['break'] = True

@trace(level=3)
def switch(ctx, ruleset):
    ctx._changes['switch'] = Switch(ruleset)

@trace(level=3)
def end(ctx):
    switch(ctx, None)
