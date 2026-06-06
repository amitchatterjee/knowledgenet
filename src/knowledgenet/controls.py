"""Rule action helpers used from then clauses.

These helpers do not mutate Factset directly. Instead they record requested
changes in ``ctx._changes`` so Session can apply merges in a deterministic
order after node execution.
"""

from knowledgenet.core.tracer import trace
from knowledgenet.ftypes import Switch

def _add_key(ctx, key, fact):
    if key not in ctx._changes:
        ctx._changes[key] = []
    ctx._changes[key].append(fact)

@trace(level=3)
def insert(ctx, fact):
    """Request insertion of fact(s) after current node completes."""
    _add_key(ctx, 'insert', fact)

@trace(level=3)
def update(ctx, fact):
    """Request update propagation for fact(s) modified in place.

    Example:
        After mutating an existing fact, call update so dependent rules can be
        re-evaluated::

            ctx.item.val = 0
            update(ctx, ctx.item)
    """
    _add_key(ctx, 'update', fact)

@trace(level=3)
def delete(ctx, fact):
    """Request deletion of fact(s) after current node completes."""
    _add_key(ctx, 'delete', fact)

@trace(level=3)
def next_ruleset(ctx):
    """Stop the current ruleset session and continue with next repository ruleset."""
    ctx._changes['break'] = True

@trace(level=3)
def switch(ctx, ruleset):
    """Stop current session and request jump to a specific ruleset id.

    Example:
        Jump from current ruleset to ``rs3``::

            switch(ctx, 'rs3')
    """
    ctx._changes['switch'] = Switch(ruleset)

@trace(level=3)
def end(ctx):
    """Stop all remaining ruleset execution for this transaction.

    Example:
        End processing when validation fails::

            if not ctx.validation.ok:
                end(ctx)
    """
    switch(ctx, None)
