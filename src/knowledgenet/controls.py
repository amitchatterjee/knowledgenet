from knowledgenet.collector import Collector
from knowledgenet.ftypes import Eval, Switch

def _add_key(ctx, key, fact):
    if key not in ctx._changes:
        ctx._changes[key] = []
    ctx._changes[key].append(fact)

def insert(ctx, fact):
    _add_key(ctx, 'insert', fact)

def update(ctx, fact):
    if type(fact) in (Collector, Eval):
        raise Exception("Updates on Collector or Eval facts not permitted")
    _add_key(ctx, 'update', fact)

def delete(ctx, fact):
    if type(fact) == Eval:
        raise Exception('Eval fact deletion is not permitted')
    _add_key(ctx, 'delete', fact)

def next_ruleset(ctx):
    ctx._changes['break'] = True

def switch(ctx, ruleset):
    ctx._changes['switch'] = Switch(ruleset)

def end(ctx):
    switch(ctx, None)
