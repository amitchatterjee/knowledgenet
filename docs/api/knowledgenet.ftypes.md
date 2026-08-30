# knowledgenet.ftypes module

Infrastructure fact types used by the runtime and rule DSL.

### *class* knowledgenet.ftypes.EventFact(group: str, on_types: list[type] | tuple[type] | set[type] | type, \*\*kwargs: object)

Bases: `object`

Tracks added, updated, and deleted facts for one event group.

EventFact is updated by Factset when matching domain facts change and can
be matched in rules through `Event(...)` or `Fact(of_type=EventFact)`.

### Example

Monitor inserts/updates/deletes of C1 facts:

```default
EventFact(group='c1-events', on_types=C1)
```

#### reset() → None

Clear accumulated change buckets for this event cycle.

### *class* knowledgenet.ftypes.Switch(ruleset: str | None)

Bases: `object`

Control-flow fact used to redirect service execution.

A `Switch` fact is emitted by control helpers and consumed by
[`knowledgenet.service.Service`](knowledgenet.service.md#knowledgenet.service.Service) after each ruleset session.

### *class* knowledgenet.ftypes.Wrapper(of_type: str | type | None = None, named: str | None = None, \*\*kwargs: object)

Bases: `object`

Named or typed wrapper fact for lightweight context injection.

Wrapper is commonly used to provide ruleset-scoped configuration and other
structured context without introducing dedicated domain classes.

### Example

Wrap a domain fact for named matching or collector aggregation:

```default
Wrapper(of_type='wrapper', wraps=C1(10))
```
