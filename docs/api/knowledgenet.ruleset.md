# knowledgenet.ruleset module

Ruleset model for grouping related rules into an execution phase.

### *class* knowledgenet.ruleset.Ruleset(id: str, rules: [Rule](knowledgenet.rule.md#knowledgenet.rule.Rule) | tuple[[Rule](knowledgenet.rule.md#knowledgenet.rule.Rule)] | list[[Rule](knowledgenet.rule.md#knowledgenet.rule.Rule)], global_ctx: dict[str, object] | None = None)

Bases: `object`

Groups related rules under one identifier.

Rules are normalized and sorted by `rule.order` before runtime execution
to produce deterministic graph insertion order.
