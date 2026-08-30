# knowledgenet.node module

Runtime node execution primitives.

Nodes are concrete rule instances bound to one matched fact combination.
Leaves cache individual when-clause evaluation outcomes to avoid recomputing
unchanged predicates after updates.

### *class* knowledgenet.node.Leaf(id, rule, when_index)

Bases: `object`

Evaluator for one when-clause bound to one fact object.

Leaf instances cache their last result and are selectively invalidated by
session update processing.

#### execute(context, fact)

Evaluate one when-clause and optionally use cached result.

* **Returns:**
  `(cached, result)` where `cached` indicates
  whether evaluation was skipped due to cache hit.
* **Return type:**
  tuple[bool, bool]

### *class* knowledgenet.node.Node(id, rule, session, when_objs)

Bases: `object`

Concrete runtime instance of a rule.

A node binds a Rule to one combination of when-clause objects and manages
predicate evaluation plus then-action execution for that binding.

#### execute(facts: set) → bool

Execute this node against current facts.

The method evaluates leaves in rule order, uses cached leaf outcomes
when possible, and executes then-actions only when all predicates pass
and at least one leaf was evaluated non-cached.

* **Returns:**
  True when then actions executed, False otherwise.
* **Return type:**
  bool

#### reset_whens(updated_facts: set) → bool

Invalidate cached leaves after fact updates.

If any bound when object is updated, this method clears cache from that
position to the end to preserve ordered predicate dependencies.
