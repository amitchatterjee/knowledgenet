# knowledgenet.factset module

Session-local fact store and indexes.

Factset tracks application facts plus infrastructure facts (Collector and
EventFact). It maintains secondary indexes used by Session for fast matching
and for propagating inserts, updates, and deletes through dependent artifacts.

### *class* knowledgenet.factset.Factset

Bases: `object`

Stores runtime facts and helper indexes for matching and projection.

#### add_facts(f: set | list) → tuple[set, set[[Collector](knowledgenet.container.md#knowledgenet.container.Collector) | [EventFact](knowledgenet.ftypes.md#knowledgenet.ftypes.EventFact)]]

Add new facts and update collector and event projections.

Returns a tuple of newly inserted facts and derived facts whose state was
updated as a result of the insertion.

#### add_to_group_collectors_dict(fact: [Collector](knowledgenet.container.md#knowledgenet.container.Collector)) → None

Register a collector in the group-to-collector index.

#### del_facts(facts: set | list) → set[[Collector](knowledgenet.container.md#knowledgenet.container.Collector) | [EventFact](knowledgenet.ftypes.md#knowledgenet.ftypes.EventFact)]

Delete facts and update indexes plus dependent helper facts.

For domain facts, collectors may remove members and events receive
deleted notifications. For Collector/EventFact facts, index entries are
removed directly.

#### find(of_type: type | str, group: str | None = None, filter: ~collections.abc.Callable[[object], bool] = <function Factset.<lambda>>) → set

Find facts by type, optionally scoped by group for helper facts.

* **Parameters:**
  * **of_type** – Target type to query. Collector and EventFact require
    `group`.
  * **group** – Logical helper group when querying Collector/EventFact.
  * **filter** – Predicate applied to each candidate result.
* **Returns:**
  Set of matching facts (possibly empty).

#### update_facts(facts: set | list) → set[[Collector](knowledgenet.container.md#knowledgenet.container.Collector) | [EventFact](knowledgenet.ftypes.md#knowledgenet.ftypes.EventFact)]

Propagate updates of existing facts to dependent helper facts.

Updating a fact can invalidate collector caches and append entries to
EventFact.updated. Returned facts are helper facts that changed as a
result of the update.
