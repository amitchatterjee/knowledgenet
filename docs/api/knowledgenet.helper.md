# knowledgenet.helper module

Convenience helpers for rule context interaction.

These utilities are intended for use in `matches` and `then` callables to
improve readability and reduce direct access to private context fields.

### knowledgenet.helper.assign(ctx: SimpleNamespace, \*\*kwargs: object) → bool

Assign values onto the rule context and return True.

This pattern enables concise match expressions such as
`assign(ctx, person=this) and this.age > 21`.

### knowledgenet.helper.factset(ctx: SimpleNamespace) → [Factset](knowledgenet.factset.md#knowledgenet.factset.Factset)

Return current session Factset for ad hoc queries.

### knowledgenet.helper.global_ctx(ctx: SimpleNamespace) → object

Return service-level global context attached to active session.

### knowledgenet.helper.node(ctx: SimpleNamespace) → [Node](knowledgenet.node.md#knowledgenet.node.Node)

Return currently executing runtime Node.

### knowledgenet.helper.session(ctx: SimpleNamespace) → Session

Return active session instance.
