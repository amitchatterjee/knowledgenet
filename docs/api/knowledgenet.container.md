# knowledgenet.container module

Collection primitives used to aggregate facts during session execution.

### *class* knowledgenet.container.Collector(group: str, of_type: type | str, filter: list[Callable] | tuple[Callable] | Callable | str = <function Collector.<lambda>>, value: Callable | None = None, key: Callable | None = None, \*\*kwargs: object)

Bases: `object`

Accumulates facts of one type and exposes aggregate operations.

Collector is itself a fact and can participate in rule matching through
`Collection(...)` or `Fact(of_type=Collector, group=...)`.

### Example

Aggregate C1 facts and expose sum/size to rules:

```default
Collector(
    of_type=C1,
    group='sum_of_c1s',
    value=lambda obj: obj.val,
)
```

#### add(obj: object) → bool

Attempt to add one fact to the collection.

Returns True only when type checks, filter checks, and deduplication all
pass and the collection actually changes.

#### empty() → bool

Return True when the collector has no facts.

#### maximum() → object

Return maximum collected fact according to configured `key` accessor.

#### minimum() → object

Return minimum collected fact according to configured `key` accessor.

#### remove(obj: object) → bool

Attempt to remove one fact from the collection.

Returns True only when the fact is currently present and passes the same
filter constraints used for insertion.

#### reset_cache() → None

Clear cached aggregate values after collection changes.

#### size() → int

Return the number of currently collected facts.

#### sum() → Number

Return sum of collected values using configured `value` accessor.

#### variance() → float

Return variance of collected values using configured `value` accessor.
