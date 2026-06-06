# knowledgenet.controls module

Rule action helpers used from then clauses.

These helpers do not mutate Factset directly. Instead they record requested
changes in `ctx._changes` so Session can apply merges in a deterministic
order after node execution.

### knowledgenet.controls.delete(ctx, fact)

Request deletion of fact(s) after current node completes.

### knowledgenet.controls.end(ctx)

Stop all remaining ruleset execution for this transaction.

### Example

End processing when validation fails:

```default
if not ctx.validation.ok:
    end(ctx)
```

### knowledgenet.controls.insert(ctx, fact)

Request insertion of fact(s) after current node completes.

### knowledgenet.controls.next_ruleset(ctx)

Stop the current ruleset session and continue with next repository ruleset.

### knowledgenet.controls.switch(ctx, ruleset)

Stop current session and request jump to a specific ruleset id.

### Example

Jump from current ruleset to `rs3`:

```default
switch(ctx, 'rs3')
```

### knowledgenet.controls.update(ctx, fact)

Request update propagation for fact(s) modified in place.

### Example

After mutating an existing fact, call update so dependent rules can be
re-evaluated:

```default
ctx.item.val = 0
update(ctx, ctx.item)
```
