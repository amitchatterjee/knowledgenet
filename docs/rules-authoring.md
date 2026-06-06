# Rules Authoring

## Introduction
This guide is intended for **rule authors** -- the engineers and business users who write the business logic for a Knowledgenet application. It covers everything you need to know to author rules: the rule syntax, matching conditions, actions, chaining, aggregation, events, and common patterns.

Before reading this guide, it is recommended that you read:
- [Concepts](concepts.md) -- foundational concepts of the Knowledgenet engine including the RETE algorithm, inferencing, and entity relationships.
- [Rule Service](rule-service.md) -- covers the platform engineering side: bootstrapping the engine, designing the fact model, configuring tracing, and wiring up transactions. Understanding the platform layer helps you understand the context in which your rules execute.

In a typical Knowledgenet application, **platform engineers** set up the infrastructure: they define the domain model (fact classes), bootstrap the engine, provide helper/utility functions, configure tracing, and wire up transaction endpoints. As a rule author, your job is to write the business logic: the individual rules that operate on facts provided by the platform.

## Understanding Facts
Facts are the data that rules operate on. They are instances of Python classes defined by the platform team as part of the domain model (see [Designing the Fact Model](rule-service.md#designing-the-fact-model) for how they are designed).

As a rule author, you need to know:
- **What types of facts exist** -- the classes defined in the domain model (e.g., `Person`, `Request`, `Claim`)
- **What attributes they have** -- the properties you can reference in match conditions (e.g., `this.age`, `this.policy.start_date`)
- **How facts flow** -- input facts are provided to the engine, rules can insert new facts, update existing facts, or delete facts, and the resulting facts flow to the next ruleset

Here is a simple example of a fact class:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
```

In your rules, you reference fact attributes in match conditions (`this.age > 21`) and in actions (`ctx.person.name`).

## Rule Structure
A rule definition consists of three main parts:

1. **Rule Attributes** - Properties that control rule behavior:
   - `id`: A globally-unique identifier for the rule. If not specified, an id is generated. For declarative rules, if the id is not specified, the name of the function containing the rule declaration is used
   - `order`: Controls execution priority (nodes with lower numbers execute first). See the [concepts documentation](concepts.md) for details on what a *node* is. If not specified, default value of *0* is used
   - `run_once`: If True, each node for the rule only executes once and is never activated again. If not specified, default value of *False* is used
   - `retrigger_on_update`: Controls whether the node is re-evaluated when one or more of the facts present in the *when* clause are updated by the *then* clause of the rule. If not specified, default value of *True* is used

2. **When (Conditions)** - Define when the rule should fire:
   - Can specify single or multiple conditions using `Fact`, `Collection`, or `Event`
   - Each condition can include a `matches` lambda/function for filtering. If not included, default value of *True* is used (the condition will always be satisfied as long as a fact of that type is present)
   - Can use `var` parameter to store matched facts in the context

3. **Then (Actions)** - Define what happens when conditions are met:
   - Can be a single function/lambda or list of functions/lambdas
   - Functions receive a context object containing matched facts
   - Common actions performed: `insert()`, `update()`, `delete()` to insert new facts, update an existing fact or delete a fact

## Your First Rule
Let's start with a simple rule that classifies a person as a minor based on age:

```python
from knowledgenet.rule import Rule, Fact
from knowledgenet.controls import insert
from knowledgenet.helper import assign

class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

class Classification:
    def __init__(self, person, category):
        self.person = person
        self.category = category

rule = Rule(
    id='classify_person',
    when=Fact(of_type=Person, matches=lambda ctx, this: this.age < 21),
    then=lambda ctx: insert(ctx, Classification(None, 'minor'))
)
```

This rule:
- Matches any `Person` fact where `age < 21`
- Inserts a new `Classification` fact with category `'minor'`

However, this rule has a problem -- we don't capture a reference to the matched person, so the `Classification` has `None` for the person. Let's fix that using `assign()` and `var`.

### Capturing Matched Facts
The `assign()` helper function stores matched facts in the context (`ctx`), making them available to the `then` clause:

```python
rule = Rule(
    id='classify_minor',
    when=Fact(of_type=Person,
              matches=lambda ctx, this: this.age < 21 and assign(ctx, person=this)),
    then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
)
```

The `assign()` function always returns `True`, so it can be chained with other conditions using `and`. After `assign(ctx, person=this)` is called, the matched `Person` fact is accessible as `ctx.person` in the `then` clause.

Alternatively, you can use the `var` parameter on the `Fact` to achieve the same result more concisely:

```python
rule = Rule(
    id='classify_minor',
    when=Fact(of_type=Person, var='person',
              matches=lambda ctx, this: this.age < 21),
    then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
)
```

When `var='person'` is specified, the matched fact is automatically stored as `ctx.person`.

### Running and Testing a Rule
To verify that your rule works, you can write a simple test. The platform team provides the `Service`, `Repository`, and `Ruleset` infrastructure (see [Rule Service](rule-service.md#bootstrapping-the-knowledgenet-engine)), but for unit tests you can create them directly:

```python
from knowledgenet.service import Service
from knowledgenet.repository import Repository
from knowledgenet.ruleset import Ruleset

repo = Repository('test', [Ruleset('rs', [rule])])
result_facts = Service(repo).execute([Person('Alice', 15), Person('Bob', 30)])

# Check results
for fact in result_facts:
    if isinstance(fact, Classification):
        print(f"{fact.person.name} is a {fact.category}")
# Output: Alice is a minor
```

The `service.execute()` call takes a list of input facts and returns all facts (input facts plus any facts inserted by rules) after rule execution completes.

## The When Clause In-Depth

### Single Fact Condition
The simplest `when` clause matches a single fact type:

```python
# Match any Person fact
Rule(when=Fact(of_type=Person), then=...)

# Match Person facts where age > 18
Rule(when=Fact(of_type=Person,
               matches=lambda ctx, this: this.age > 18),
     then=...)
```

The `matches` parameter receives two arguments:
- `ctx` - the context namespace (a `SimpleNamespace`), shared across all conditions in the rule
- `this` - the fact being evaluated

### Multiple Match Conditions on a Single Fact
You can pass a list of match functions. All must return `True` for the condition to be satisfied (AND logic):

```python
Rule(
    when=Fact(of_type=Person,
              matches=[
                  lambda ctx, this: this.age >= 16,
                  lambda ctx, this: this.name.startswith('A')
              ]),
    then=...
)
```

This is equivalent to combining the conditions with `and` in a single lambda, but can be clearer for complex conditions.

### Multiple Fact Conditions
When the `when` clause contains a list of `Fact` conditions, **all** conditions must be satisfied for the rule to fire:

```python
class Address:
    def __init__(self, person_id, city):
        self.person_id = person_id
        self.city = city

class PersonProfile:
    def __init__(self, person, address):
        self.person = person
        self.address = address

rule = Rule(
    id='build_profile',
    when=[
        Fact(of_type=Person,
             matches=lambda ctx, this: assign(ctx, person=this)),
        Fact(of_type=Address,
             matches=lambda ctx, this: this.person_id == ctx.person.name
                     and assign(ctx, addr=this))
    ],
    then=lambda ctx: insert(ctx, PersonProfile(ctx.person, ctx.addr))
)
```

**Important**: When multiple `Fact` conditions are present, Knowledgenet creates **nodes** for every valid combination of matching facts. For example, if there are 2 `Person` facts and 3 `Address` facts, the engine evaluates all 6 combinations (2 x 3) and creates nodes only for those where all conditions are satisfied.

The conditions are evaluated in order. Context variables set by earlier conditions (via `assign()` or `var`) are available to later conditions. In the example above, `ctx.person` set in the first condition is used in the second condition to correlate the address with the person.

### Named Facts
Instead of matching by Python type, you can match facts by a string name. Named facts are created using the `Wrapper` class (typically by the platform team) and matched using `Fact(named=...)`:

```python
# Matching a named fact provided by the platform
rule = Rule(
    when=[
        Fact(named='validation-ruleset', var='ruleset_context'),
        Fact(of_type=Request, var='request',
             matches=lambda ctx, this: not this.policy)
    ],
    then=lambda ctx: insert(ctx, create_action(ctx, ctx.ruleset_context, ctx.request))
)
```

Named facts are commonly used to pass ruleset-level configuration from the platform to rules. See [Wrappers](rule-service.md#wrappers-named-facts) in the Rule Service documentation for how they are created.

### The Wrapper Class
You can also create `Wrapper` facts directly in rules when you need lightweight, ad-hoc fact types:

```python
from knowledgenet.ftypes import Wrapper

# Named wrapper - identified by string name
w1 = Wrapper(named='my-context', key='value', count=10)

# Typed wrapper with a string type
w2 = Wrapper(of_type='custom-type', data=[1, 2, 3])

# Wrapper around an existing object
w3 = Wrapper(named='wrapped-item', wraps=some_object)
# Access the wrapped object via: w3.wraps
```

Wrappers are hashable and their identity is determined by their `of_type`/`named` value plus their keyword arguments. Two wrappers with the same name and arguments are considered equal.

## The Then Clause In-Depth

### Lambda Actions
For simple actions, use lambda expressions:

```python
Rule(
    when=Fact(of_type=Person, var='p'),
    then=lambda ctx: insert(ctx, Classification(ctx.p, 'processed'))
)
```

### Function Actions
For complex logic, define a separate function. These functions are often placed in the same module as the rule:

```python
def classify_person(ctx):
    person = ctx.person
    if person.age < 13:
        category = 'child'
    elif person.age < 18:
        category = 'teenager'
    else:
        category = 'adult'
    insert(ctx, Classification(person, category))

rule = Rule(
    id='classify_person',
    when=Fact(of_type=Person, var='person'),
    then=classify_person
)
```

### Multiple Actions
The `then` clause can accept a list of functions. They are executed in order:

```python
rule = Rule(
    id='process_order',
    when=Fact(of_type=Order, var='order'),
    then=[
        lambda ctx: insert(ctx, AuditLog(ctx.order, 'processed')),
        lambda ctx: insert(ctx, Receipt(ctx.order))
    ]
)
```

### Control Functions
Knowledgenet provides the following control functions for use in `then` clauses. All are imported from `knowledgenet.controls`:

#### insert(ctx, fact)
Inserts a new fact into the FactSet. The new fact may trigger creation of new nodes for rules that match the inserted fact type:

```python
from knowledgenet.controls import insert

then=lambda ctx: insert(ctx, NewFact(value=42))
```

You can also insert multiple facts by passing a list:

```python
then=lambda ctx: insert(ctx, [Fact1(), Fact2()])
```

#### update(ctx, fact)
Signals that a fact has been modified. You must call `update()` after modifying a fact's attributes so the engine knows to re-evaluate rules that depend on it:

```python
from knowledgenet.controls import update

def modify_person(ctx):
    ctx.person.age = ctx.person.age + 1
    update(ctx, ctx.person)
```

When a fact is updated, all nodes containing that fact have their cached evaluation results invalidated, and the execution cursor may move backward in the graph to re-evaluate affected rules.

#### delete(ctx, fact)
Removes a fact from the FactSet. All nodes containing the deleted fact are removed from the execution graph:

```python
from knowledgenet.controls import delete

then=lambda ctx: delete(ctx, ctx.obsolete_fact)
```

You can also delete multiple facts by passing a list:

```python
then=lambda ctx: delete(ctx, [fact1, fact2])
```

#### next_ruleset(ctx)
Terminates the current ruleset's execution and proceeds to the next ruleset in the repository:

```python
from knowledgenet.controls import next_ruleset

# Skip remaining rules in this ruleset
then=lambda ctx: next_ruleset(ctx)
```

#### switch(ctx, ruleset_id)
Terminates the current ruleset and jumps to a specific ruleset by its id:

```python
from knowledgenet.controls import switch

# Jump to the 'error-handling' ruleset, skipping intermediate ones
then=lambda ctx: switch(ctx, 'error-handling')
```

#### end(ctx)
Terminates all rule execution. No further rulesets are processed:

```python
from knowledgenet.controls import end

# Stop processing entirely
then=lambda ctx: end(ctx)
```

Internally, `end(ctx)` is equivalent to `switch(ctx, None)`.

### Helper Functions
Knowledgenet provides helper functions imported from `knowledgenet.helper`:

#### assign(ctx, **kwargs) -> bool
Stores named values in the context. Always returns `True` so it can be used in match expressions:

```python
from knowledgenet.helper import assign

# In a match expression - store a computed value for use in the then clause
matches=lambda ctx, this: assign(ctx, total=this.price * this.quantity) and ctx.total > 100
```

#### factset(ctx) -> Factset
Returns the current `Factset` object, allowing direct queries against all facts in the system:

```python
from knowledgenet.helper import factset

# Query facts by type
all_orders = factset(ctx).find(of_type=Order)

# Query with a filter
large_orders = factset(ctx).find(of_type=Order, filter=lambda o: o.amount > 1000)

# Query collectors by group
collectors = factset(ctx).find(of_type=Collector, group='my-collector')
```

#### node(ctx) -> Node
Returns the current `Node` object (the rule instance being executed):

```python
from knowledgenet.helper import node

current_node = node(ctx)
# Access the rule: current_node.rule.id
```

#### session(ctx) -> Session
Returns the current `Session` object:

```python
from knowledgenet.helper import session

current_session = session(ctx)
```

#### global_ctx(ctx) -> dict
Returns the global context dictionary shared across all rule executions within a service. This is configured by the platform team when creating the `Service` (see [Global Context](rule-service.md#global-context)):

```python
from knowledgenet.helper import global_ctx

def lookup_data(ctx):
    client = global_ctx(ctx)['api_client']
    result = client.lookup(ctx.request.id)
    insert(ctx, ExternalData(result))
```

## Rule Chaining
One of the most powerful features of a RETE engine is **rule chaining** -- where the output of one rule becomes the input for another. This happens automatically when rules insert, update, or delete facts.

### Forward Chaining with Insert
When a rule inserts a new fact, any other rule whose `when` clause matches the new fact type will be evaluated:

```python
class RawData:
    def __init__(self, value):
        self.value = value

class ValidatedData:
    def __init__(self, data):
        self.data = data

class ProcessedResult:
    def __init__(self, data):
        self.data = data

# Rule 1: Validate raw data
rule_validate = Rule(
    id='validate',
    when=Fact(of_type=RawData, var='raw',
              matches=lambda ctx, this: this.value > 0),
    then=lambda ctx: insert(ctx, ValidatedData(ctx.raw))
)

# Rule 2: Process validated data (fires automatically when ValidatedData is inserted)
rule_process = Rule(
    id='process',
    when=Fact(of_type=ValidatedData, var='validated'),
    then=lambda ctx: insert(ctx, ProcessedResult(ctx.validated))
)
```

### Backward Chaining with Update
When a rule updates a fact, the engine re-evaluates rules that previously matched (or failed to match) that fact. The execution cursor moves backward in the graph to the leftmost affected node:

```python
# Rule 1: Fire when value is zero (does NOT match initially)
rule_1 = Rule(
    id='r1',
    when=Fact(of_type=Item, var='item',
              matches=lambda ctx, this: this.value == 0),
    then=lambda ctx: insert(ctx, ZeroValueAlert(ctx.item))
)

# Rule 2: Set value to zero (fires first because of higher order)
def reset_value(ctx):
    ctx.item.value = 0
    update(ctx, ctx.item)

rule_2 = Rule(
    id='r2', order=1,
    when=Fact(of_type=Item, var='item',
              matches=lambda ctx, this: this.value > 0),
    then=reset_value
)
```

In this example:
1. `rule_2` (order=1) fires first, setting the item's value to 0 and calling `update()`
2. The engine detects the update and moves the cursor back
3. `rule_1` (order=0) is re-evaluated, now matches (`value == 0`), and fires

This backward movement is what makes RETE networks fundamentally different from simple pipeline architectures.

### Chain Termination with Delete
When a rule deletes a fact, all nodes that contain the deleted fact are removed from the graph, preventing those rules from firing:

```python
# Rule 1: Delete invalid items
rule_1 = Rule(
    id='remove_invalid',
    when=Fact(of_type=Item, var='item',
              matches=lambda ctx, this: this.value < 0),
    then=lambda ctx: delete(ctx, ctx.item)
)

# Rule 2: Process items (won't fire for deleted items)
rule_2 = Rule(
    id='process_item', order=1,
    when=Fact(of_type=Item, var='item',
              matches=lambda ctx, this: assign(ctx, i=this)),
    then=lambda ctx: insert(ctx, ProcessedItem(ctx.i))
)
```

### Combinations and Permutations
When a rule has multiple `when` conditions, Knowledgenet creates nodes for **every valid combination** of matching facts. This is a key aspect of the RETE algorithm:

```python
rule = Rule(
    id='pair_people',
    when=[
        Fact(of_type=Person, matches=lambda ctx, this: assign(ctx, p=this)),
        Fact(of_type=City, matches=lambda ctx, this: assign(ctx, c=this))
    ],
    then=lambda ctx: insert(ctx, Assignment(ctx.p, ctx.c))
)

# With 2 persons and 3 cities, this creates 2 x 3 = 6 nodes
facts = [Person('Alice', 25), Person('Bob', 30),
         City('NYC'), City('LA'), City('Chicago')]
# 6 Assignment facts are created
```

To create only correlated combinations (not a Cartesian product), use cross-referencing in the match conditions:

```python
rule = Rule(
    id='match_person_address',
    when=[
        Fact(of_type=Person, matches=lambda ctx, this: assign(ctx, person=this)),
        Fact(of_type=Address,
             matches=lambda ctx, this: this.person_id == ctx.person.name
                     and assign(ctx, addr=this))
    ],
    then=lambda ctx: insert(ctx, PersonProfile(ctx.person, ctx.addr))
)
```

## Collections and Aggregation
Collections allow you to group facts by type and compute aggregate values. This is essential for rules that need to operate on multiple facts as a set rather than individually.

### The Collector
A `Collector` is a special fact type that automatically aggregates facts of a specified type. Collectors are typically provided by the platform team as part of the input facts (see [Collectors](rule-service.md#collectors) in the Rule Service documentation), but they can also be inserted by rules at runtime.

To use a collector in a rule, match it using `Collection` or `Fact(of_type=Collector, group=...)`:

```python
from knowledgenet.rule import Rule, Fact, Collection
from knowledgenet.container import Collector

class OrderItem:
    def __init__(self, name, price, quantity):
        self.name = name
        self.price = price
        self.quantity = quantity

class OrderSummary:
    def __init__(self, total, count):
        self.total = total
        self.count = count

# Rule that fires when the sum of all items exceeds a threshold
rule = Rule(
    id='check_order_total',
    when=Collection(group='order_items',
                    matches=lambda ctx, this: this.sum() > 100
                            and assign(ctx, total=this.sum(), count=this.size())),
    then=lambda ctx: insert(ctx, OrderSummary(ctx.total, ctx.count))
)
```

The `Collection` class is syntactic sugar for `Fact(of_type=Collector, group=...)`. Using `Collection` is recommended for clarity.

### Collector Aggregate Methods
Within a match condition, the `this` parameter refers to the `Collector` object, which provides these aggregation methods:

| Method | Description | Requires |
|--------|-------------|----------|
| `sum()` | Sum of all collected values | `value` parameter on Collector |
| `variance()` | Statistical variance of collected values | `value` parameter on Collector |
| `minimum()` | Fact with the minimum key | `key` parameter on Collector |
| `maximum()` | Fact with the maximum key | `key` parameter on Collector |
| `size()` | Number of collected facts | - |
| `empty()` | `True` if no facts collected | - |
| `collection` | The set of collected fact objects | - |

### Accessing the Collection Directly
Use the `collection` attribute to iterate over or sort collected facts:

```python
def select_best_action(ctx):
    actions = list(ctx.actions.collection)
    actions.sort(key=lambda a: (-a.rank, a.pay_percent))
    best = actions[0]
    best.inactive = False
    update(ctx, best)

rule = Rule(
    id='select_action',
    run_once=True, order=1,
    when=Collection(group='action-collector', var='actions',
                    matches=lambda ctx, this: not this.empty()),
    then=select_best_action
)
```

### Inserting Collectors from Rules
Collectors can be inserted dynamically from rule actions. This is useful when you need to create per-entity aggregations:

```python
class Parent:
    def __init__(self, id):
        self.id = id

class Child:
    def __init__(self, parent, value):
        self.parent = parent
        self.value = value

# Create a collector for each parent
rule_create_collectors = Rule(
    id='create_collectors',
    when=Fact(of_type=Parent, var='parent'),
    then=lambda ctx: insert(ctx,
        Collector(of_type=Child, group='children',
                  parent=ctx.parent,
                  filter=lambda collector, child: child.parent == collector.parent,
                  value=lambda child: child.value))
)
```

Note that the `filter` function receives the collector instance as the first argument. This allows filters that reference custom attributes stored on the collector (like `collector.parent` above).

### Automatic Collector Updates
Collectors automatically update when facts are inserted, updated, or deleted during rule execution. When a collector's contents change, rules that depend on it are re-evaluated:

```python
rule_add_item = Rule(
    id='add_bonus_item',
    when=Fact(of_type=Order, var='order',
              matches=lambda ctx, this: this.qualifies_for_bonus),
    then=lambda ctx: insert(ctx, OrderItem('Bonus', 0, 1))
)

# This rule automatically re-evaluates when the new OrderItem is added to the collector
rule_check_total = Rule(
    id='check_total', order=1,
    when=Collection(group='order_items', var='items'),
    then=lambda ctx: insert(ctx, Summary(ctx.items.sum(), ctx.items.size()))
)
```

## Events
Events allow rules to react to changes in the FactSet (insertions, updates, and deletions of specific fact types) rather than matching individual facts. Events are typically set up by the platform team as part of the input facts (see [EventFacts](rule-service.md#eventfacts) in the Rule Service documentation).

### Event Rules
Use the `Event` condition in the `when` clause to match events:

```python
from knowledgenet.rule import Event

rule = Rule(
    id='on_item_change',
    when=Event(group='item-changes', var='event'),
    then=lambda ctx: handle_change(ctx, ctx.event)
)
```

The `Event` class is syntactic sugar for `Fact(of_type=EventFact, group=...)`.

### Event Properties
When an event fires, the `EventFact` object (accessible via `ctx.event` if `var='event'`) provides:

| Property | Description |
|----------|-------------|
| `added` | Set of facts that were added |
| `updated` | Set of facts that were updated |
| `deleted` | Set of facts that were deleted |

```python
def handle_change(ctx, event):
    for added_fact in event.added:
        insert(ctx, AuditLog('added', added_fact))
    for updated_fact in event.updated:
        insert(ctx, AuditLog('updated', updated_fact))
    for deleted_fact in event.deleted:
        insert(ctx, AuditLog('deleted', deleted_fact))
```

### Events with Aggregation
Events are commonly used with `factset()` to compute aggregates across all facts of a type when any change occurs:

```python
from knowledgenet.helper import factset

rule = Rule(
    id='recompute_total',
    when=Event(group='item-events',
               matches=lambda ctx, this:
                   assign(ctx, total=sum(
                       item.price for item in factset(ctx).find(of_type=OrderItem)
                   )) and ctx.total > 0),
    then=lambda ctx: insert(ctx, OrderTotal(ctx.total))
)
```

### Creating EventFacts in Rules
While EventFacts are typically provided by the platform team, you can also create them in rules when needed:

```python
from knowledgenet.ftypes import EventFact

rule = Rule(
    id='setup_monitoring',
    when=Fact(of_type=Config, var='config',
              matches=lambda ctx, this: this.enable_audit),
    then=lambda ctx: insert(ctx, EventFact(group='audit', on_types=[Action, Payment]))
)
```

## Declarative Rules with @ruledef
The `@ruledef` decorator is the recommended way to define rules. It provides a clean way to define rules in separate Python modules that are automatically discovered and registered by the platform's scanner.

### Basic Usage

```python
from knowledgenet.decorator import ruledef
from knowledgenet.rule import Rule, Fact
from knowledgenet.controls import insert
from knowledgenet.helper import assign

@ruledef
def classify_minor():
    return Rule(
        when=Fact(of_type=Person, var='person',
                  matches=lambda ctx, this: this.age < 21),
        then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
    )
```

When `@ruledef` is used without arguments:
- The **rule id** is derived from the function name (`classify_minor`)
- The **ruleset id** is derived from the parent directory name
- The **repository id** is derived from the grandparent directory name

This means the file's location in the directory structure determines which ruleset and repository the rule belongs to. See [Directory Structure Convention](rule-service.md#directory-structure-convention) in the Rule Service documentation for how platform engineers organize the directory layout.

### With Explicit Parameters

```python
@ruledef(id='custom-rule-id', ruleset='my-ruleset', repository='my-repo')
def classify_minor():
    return Rule(
        when=Fact(of_type=Person, var='person',
                  matches=lambda ctx, this: this.age < 21),
        then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
    )
```

### Disabling Rules

```python
@ruledef(enabled=False)
def deprecated_rule():
    return Rule(...)
```

A disabled rule is not registered with the engine. This is useful during development or for temporarily removing a rule without deleting the code.

## Rule Execution Order

### The Order Attribute
The `order` attribute controls the relative execution priority of rules within a ruleset. Rules with lower `order` values execute first:

```python
rule_a = Rule(id='first', order=0, when=..., then=...)   # Executes first
rule_b = Rule(id='second', order=1, when=..., then=...)  # Executes second
rule_c = Rule(id='third', order=2, when=..., then=...)   # Executes third
```

The default `order` is `0`. Rules with the same order value have their nodes placed in the graph without a guaranteed relative order.

**Tip**: Use `order` to ensure that certain rules fire before others. For example, validation rules at `order=0` and aggregate/summary rules at `order=1` ensures that all individual validations complete before the summary rule evaluates.

## Controlling Rule Re-execution

### run_once
When `run_once=True`, a rule's node is removed from the graph after its first execution, regardless of subsequent fact changes:

```python
rule = Rule(
    id='initialize',
    run_once=True,
    when=Fact(of_type=Config, var='config'),
    then=lambda ctx: insert(ctx, InitResult(ctx.config))
)
```

Use `run_once` for:
- Validation rules where you want a single check per request
- Initialization rules that should fire exactly once per matching fact combination
- Preventing infinite loops when a rule modifies facts that would cause it to re-trigger

### retrigger_on_update
When `retrigger_on_update=False`, a rule will not re-execute if the facts it matched are updated:

```python
def halve_value(ctx):
    ctx.item.value = ctx.item.value // 2
    update(ctx, ctx.item)

rule = Rule(
    id='halve',
    retrigger_on_update=False,
    when=Fact(of_type=Item, var='item'),
    then=halve_value
)
```

Without `retrigger_on_update=False`, this rule would create an infinite loop: it updates the fact, which triggers re-evaluation, which updates the fact again, and so on.

### run_once vs retrigger_on_update
These two attributes address different scenarios:

- `run_once=True`: The node is **permanently removed** from the graph after first execution. It will never fire again for that fact combination.
- `retrigger_on_update=False`: The node **stays in the graph** but its cached evaluation result is not invalidated when its matched facts are updated. It can still fire again if new fact combinations are created (e.g., via insert).

## Flow Control Across Rulesets
Rulesets within a repository execute in sequence by default. The output of each ruleset feeds into the next. Rules can alter this flow using the control functions described below.

### Normal Flow

```
Ruleset 1 → Ruleset 2 → Ruleset 3 → Result
```

### Skipping a Ruleset with next_ruleset()
`next_ruleset(ctx)` terminates the current ruleset and proceeds to the next one. Remaining rules in the current ruleset are skipped:

```python
# If validation fails, skip remaining validation rules
rule = Rule(
    id='skip_on_error',
    when=Fact(of_type=ValidationError),
    then=lambda ctx: next_ruleset(ctx)
)
```

### Jumping to a Specific Ruleset with switch()
`switch(ctx, ruleset_id)` terminates the current ruleset and jumps directly to the specified ruleset, skipping any intermediate ones:

```python
# In a rule within the first ruleset:
then=lambda ctx: switch(ctx, 'error-handling')
# Skips all rulesets between current and 'error-handling'
```

This enables conditional workflow routing, such as jumping to error handling or skipping optional processing phases.

### Ending Execution with end()
`end(ctx)` terminates all rule execution immediately. No further rulesets are processed:

```python
# Critical error: stop all processing
rule = Rule(
    id='critical_stop',
    when=Fact(of_type=CriticalError),
    then=lambda ctx: end(ctx)
)
```

## Practical Patterns

### Validation Pattern
A common pattern is to run validation rules first and terminate early if validation fails:

```python
class ValidationError:
    def __init__(self, message):
        self.message = message

# Check for required fields
validate_required = Rule(
    id='validate_required',
    run_once=True,
    when=Fact(of_type=Request, var='req',
              matches=lambda ctx, this: not this.customer_id),
    then=lambda ctx: insert(ctx, ValidationError('customer_id is required'))
)

# Stop processing if validation errors exist
stop_on_error = Rule(
    id='stop_on_error',
    order=1,
    when=Fact(of_type=ValidationError),
    then=lambda ctx: end(ctx)
)
```

### Accumulator Pattern
Use collectors to accumulate results and make decisions based on aggregates:

```python
class Score:
    def __init__(self, category, points):
        self.category = category
        self.points = points

class RiskAssessment:
    def __init__(self, total_score, risk_level):
        self.total_score = total_score
        self.risk_level = risk_level

# Individual scoring rules
rule_age = Rule(
    id='score_age',
    run_once=True,
    when=Fact(of_type=Person, var='p',
              matches=lambda ctx, this: this.age < 25),
    then=lambda ctx: insert(ctx, Score('age', 10))
)

rule_history = Rule(
    id='score_history',
    run_once=True,
    when=Fact(of_type=DrivingRecord, var='record',
              matches=lambda ctx, this: this.accidents > 0),
    then=lambda ctx: insert(ctx, Score('history', 20))
)

# Aggregation rule (requires a Collector(of_type=Score, group='scores', value=...)
# to be provided in the input facts)
rule_assess = Rule(
    id='assess_risk',
    run_once=True, order=1,
    when=Collection(group='scores',
                    matches=lambda ctx, this:
                        assign(ctx, total=this.sum())
                        and not this.empty()),
    then=lambda ctx: insert(ctx,
        RiskAssessment(ctx.total,
                       'high' if ctx.total > 20 else 'low'))
)
```

### Selection Pattern
Select the best option from a collection:

```python
def select_best(ctx):
    candidates = list(ctx.candidates.collection)
    candidates.sort(key=lambda c: (-c.rank, c.cost))
    best = candidates[0]
    best.selected = True
    update(ctx, best)

rule_select = Rule(
    id='select_best',
    run_once=True, order=1,
    when=Collection(group='candidates', var='candidates',
                    matches=lambda ctx, this: not this.empty()),
    then=select_best
)
```

### Event Auditing Pattern
Track all fact changes for auditing:

```python
def audit_changes(ctx, event):
    for fact in event.added:
        insert(ctx, AuditEntry('CREATED', type(fact).__name__, str(fact)))
    for fact in event.updated:
        insert(ctx, AuditEntry('UPDATED', type(fact).__name__, str(fact)))
    for fact in event.deleted:
        insert(ctx, AuditEntry('DELETED', type(fact).__name__, str(fact)))

rule_audit = Rule(
    id='audit_trail',
    when=Event(group='audit', var='event'),
    then=lambda ctx: audit_changes(ctx, ctx.event)
)
```

### Multi-Phase Pipeline
Organize complex business logic into distinct ruleset phases:

```python
# Directory structure:
# rules/claims/
#   01_validation/        <- Validates input data
#     field_validation.py
#     business_validation.py
#   02_eligibility/       <- Evaluates contract terms
#     contract_rules.py
#     coverage_rules.py
#   03_fraud/             <- Flags suspicious claims
#     fraud_detection.py
#   04_pricing/           <- Computes payment amounts
#     pricing_rules.py
#   05_finalization/      <- Selects the best action
#     selection_rules.py

# Each phase operates on the facts produced by the previous phase.
# Rules in each phase focus on a single concern.
```

## Avoiding Common Pitfalls

### Infinite Loops
The most common pitfall is creating rules that trigger themselves infinitely. This happens when a rule updates a fact that it also matches:

```python
# DANGER: Infinite loop
rule = Rule(
    when=Fact(of_type=Item, var='item'),
    then=lambda ctx: (setattr(ctx.item, 'count', ctx.item.count + 1),
                      update(ctx, ctx.item))
)
```

**Solutions:**
- Use `run_once=True` if the rule should fire exactly once per fact
- Use `retrigger_on_update=False` if the rule should not re-fire when it updates its own facts
- Add a guard condition to the match (e.g., `this.count < 10`)

### Unintended Combinations
Multi-condition rules generate all valid combinations. Be explicit about correlations:

```python
# PROBLEM: Creates Cartesian product of all persons x all addresses
rule = Rule(
    when=[Fact(of_type=Person, var='p'), Fact(of_type=Address, var='a')],
    then=...
)

# SOLUTION: Correlate the conditions
rule = Rule(
    when=[
        Fact(of_type=Person, var='p'),
        Fact(of_type=Address, var='a',
             matches=lambda ctx, this: this.person_id == ctx.p.id)
    ],
    then=...
)
```

### Facts Must Be Hashable
All facts stored in the FactSet must be hashable. If the platform team defines `__eq__` on a fact class, they must also define `__hash__`. If you create ad-hoc fact classes in your rules, remember this requirement:

```python
# WRONG: Defining __eq__ without __hash__ makes the object unhashable
class Item:
    def __eq__(self, other):
        return self.id == other.id
    # Missing __hash__!

# CORRECT: Define both
class Item:
    def __eq__(self, other):
        return isinstance(other, Item) and self.id == other.id
    def __hash__(self):
        return hash(self.id)
```

### Order Matters in Multi-Condition Rules
Context variables set in earlier conditions are available to later ones. Arrange conditions so that variables are assigned before they are referenced:

```python
# WRONG: ctx.person is not set when Address is evaluated
rule = Rule(
    when=[
        Fact(of_type=Address,
             matches=lambda ctx, this: this.person_id == ctx.person.id),  # Error!
        Fact(of_type=Person, var='person')
    ],
    then=...
)

# CORRECT: Person is matched first, setting ctx.person
rule = Rule(
    when=[
        Fact(of_type=Person, var='person'),
        Fact(of_type=Address,
             matches=lambda ctx, this: this.person_id == ctx.person.id)
    ],
    then=...
)
```

## Testing Rules
Well-tested rules are critical for a reliable system. For unit tests, you can create a minimal `Service` / `Repository` / `Ruleset` setup without needing the full platform bootstrap.

### Basic Test Structure

```python
import pytest
from knowledgenet.service import Service
from knowledgenet.repository import Repository
from knowledgenet.ruleset import Ruleset
from knowledgenet.rule import Rule, Fact
from knowledgenet.controls import insert

def find_results(result_type, facts):
    """Helper to filter results by type."""
    return [f for f in facts if isinstance(f, result_type)]

def test_classify_minor():
    rule = Rule(
        id='classify_minor',
        when=Fact(of_type=Person, var='person',
                  matches=lambda ctx, this: this.age < 21),
        then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
    )
    repo = Repository('test', [Ruleset('rs', [rule])])
    result = Service(repo).execute([Person('Alice', 15)])

    classifications = find_results(Classification, result)
    assert len(classifications) == 1
    assert classifications[0].category == 'minor'

def test_no_classification_for_adults():
    rule = Rule(
        id='classify_minor',
        when=Fact(of_type=Person, var='person',
                  matches=lambda ctx, this: this.age < 21),
        then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
    )
    repo = Repository('test', [Ruleset('rs', [rule])])
    result = Service(repo).execute([Person('Bob', 30)])

    classifications = find_results(Classification, result)
    assert len(classifications) == 0
```

### Testing with Collections

```python
def test_aggregate_scoring():
    from knowledgenet.container import Collector

    facts = [
        Score('age', 10),
        Score('history', 20),
        Collector(of_type=Score, group='scores',
                  value=lambda s: s.points)
    ]
    repo = Repository('test', [Ruleset('rs', [rule_assess])])
    result = Service(repo).execute(facts)

    assessments = find_results(RiskAssessment, result)
    assert len(assessments) == 1
    assert assessments[0].total_score == 30
    assert assessments[0].risk_level == 'high'
```

### Testing Flow Control

```python
def test_validation_stops_execution():
    business_rule = Rule(id='business',
                         when=Fact(of_type=Request),
                         then=lambda ctx: insert(ctx, Result('processed')))
    repo = Repository('test', [
        Ruleset('validation', [validate_required, stop_on_error]),
        Ruleset('business', [business_rule])
    ])

    result = Service(repo).execute([Request(customer_id=None)])

    errors = find_results(ValidationError, result)
    assert len(errors) == 1
    results = find_results(Result, result)
    assert len(results) == 0  # Business rules were skipped
```

## Quick Reference

### Imports for Rule Authors

```python
# Rule definition
from knowledgenet.rule import Rule, Fact, Collection, Event
from knowledgenet.decorator import ruledef

# Control functions (used in then clauses)
from knowledgenet.controls import insert, update, delete, switch, next_ruleset, end

# Helper functions (used in when and then clauses)
from knowledgenet.helper import assign, factset, node, session, global_ctx

# Fact types (when creating facts in rules)
from knowledgenet.container import Collector
from knowledgenet.ftypes import EventFact, Wrapper
```

### Rule Skeleton

```python
Rule(
    id='rule-id',                       # Optional: unique identifier
    order=0,                            # Optional: execution priority (lower first)
    run_once=False,                     # Optional: fire only once per node
    retrigger_on_update=True,           # Optional: re-fire when matched facts update
    when=Fact(                          # Single condition
        of_type=MyClass,               #   or named='string-name'
        var='my_var',                  #   Optional: context variable name
        matches=lambda ctx, this: ...  #   Optional: filter expression
    ),
    then=lambda ctx: ...               # Action(s) to perform
)
```

### @ruledef Skeleton

```python
@ruledef                                    # Auto-derive ids from function/directory
# or
@ruledef(id='...', ruleset='...', repository='...', enabled=True)
def rule_name():
    return Rule(
        when=...,
        then=...
    )
```
