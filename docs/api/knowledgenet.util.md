# knowledgenet.util module

General-purpose utility helpers shared across Knowledgenet modules.

### knowledgenet.util.merge(d1: dict[str, Any], d2: dict[str, Any]) → dict[str, Any]

Recursively merge two dictionaries, preferring right-hand values.

Nested dict values are merged recursively, list values are merged by index,
and scalar conflicts are resolved in favor of `d2`.

### knowledgenet.util.of_type(fact)

Return the effective type for a fact.

Wrapper facts expose their logical `of_type` instead of concrete Wrapper
class to support named/typed matching semantics.

### knowledgenet.util.to_frozenset(obj)

Convert a scalar or iterable value into a frozenset.

### knowledgenet.util.to_list(obj)

Convert a scalar or iterable value into a list.

Scalars become single-item lists.

### knowledgenet.util.to_tuple(obj)

Convert a scalar or iterable value into a tuple.

Scalars become single-item tuples.
