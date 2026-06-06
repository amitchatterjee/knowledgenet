# knowledgenet.repository module

Repository model grouping ordered rulesets for one service.

### *class* knowledgenet.repository.Repository(id: str, rulesets: list[[Ruleset](knowledgenet.ruleset.md#knowledgenet.ruleset.Ruleset)])

Bases: `object`

Defines a named repository with executable rulesets.

Service executes rulesets in listed order unless flow-control actions
request early termination or switching to a specific ruleset.
