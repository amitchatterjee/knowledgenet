# knowledgenet.service module

Service entrypoint for transactional RETE execution.

The service coordinates end-to-end execution of a repository, where each
ruleset is executed in its own runtime session. Facts emitted from one session
become inputs to the next session unless flow-control facts change the path.

### *class* knowledgenet.service.Service(repository: [Repository](knowledgenet.repository.md#knowledgenet.repository.Repository), id: str = 'knowledgenet', global_ctx: dict[str, object] | None = None, node_sorter: Callable[[[Node](knowledgenet.node.md#knowledgenet.node.Node), [Node](knowledgenet.node.md#knowledgenet.node.Node)], int] | None = None)

Bases: `object`

Coordinates repository execution across rulesets.

A service is typically initialized once during application startup and
reused for many transactions. Each call to [`execute()`](#knowledgenet.service.Service.execute) processes one
transaction and returns the final fact set produced by chained rulesets.

#### execute(facts: set | list, start_from: str | None = None, trc_level: int = 0, trc_details: int = 0) → set | list

Execute a transaction against the repository.

* **Parameters:**
  * **facts** – Initial transaction facts.
  * **start_from** – Optional ruleset id to start from instead of the first
    repository ruleset.
  * **trc_level** – Runtime trace verbosity threshold.
  * **trc_details** – Runtime trace payload detail level.
* **Returns:**
  Final set of facts after all reachable rulesets complete.

### Examples

Basic transaction execution:

```default
result_facts = Service(repo).execute([C1(10), C1(20)])
```

Resume execution from a specific ruleset:

```default
result_facts = Service(repo).execute(facts, start_from='rs2')
```
