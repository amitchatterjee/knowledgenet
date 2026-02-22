# Rules Authoring

## Introduction
The Knowledgenet framework provides a flexible and powerful way to define, manage, and execute business rules in Python. This guide will walk you through the process of authoring rules using Knowledgenet, from basic rule creation to advanced patterns and best practices.

As discussed in [rules-service documentation](rule-service.md), Knowledgenet rules can be created in two ways:
1. **Programmatically** - by directly instantiating `Rule` objects in your initialization code.
2. **Declaratively** - using Python functions decorated with `@ruledef`, which automatically registers rules with the framework.

The declarative approach with `@ruledef` makes rules easier to write, test, and maintain as separate modules. Rules are organized into rulesets and repositories, allowing for logical grouping and modular deployment of business logic.

Before reading this guide, it is recommended that you read the [Concepts](concepts.md) document, which covers the foundational concepts of the Knowledgenet engine including the RETE algorithm, inferencing, and entity relationships.

## About the knowledgenet-examples companion project
The `knowledgenet-examples` companion project is designed to provide practical examples and a reference implementation of a typical Knowledgenet rules system. By exploring this repository, you can gain insights into how to structure and implement rules within the Knowledgenet framework. Please visit the [Knowledgenet Examples Repository](https://github.com/amitchatterjee/knowledgenet-examples), download/clone the repository to follow along. Here are some key functionalities and features you might find in the `knowledgenet-examples` project:

1. **Rule Definitions**: Examples of how to define rules using Python, including syntax and best practices.
2. **Rule Execution**: Demonstrations of how rules are executed within the Knowledgenet system.
3. **Integration**: Examples showing how to integrate Knowledgenet rules with other systems or applications.
4. **Testing**: Sample unit tests to ensure that rules are functioning as expected.
5. **Documentation**: Detailed comments and documentation within the code to explain the purpose and functionality of different components.

To get started, you can clone the repository using the following command from your terminal:

```bash
git clone https://github.com/amitchatterjee/knowledgenet-examples.git
```
Once cloned, you can navigate through the project files and follow the examples provided to understand how to implement and work with Knowledgenet rules.

## Defining Facts
Facts are the fundamental data units that rules operate on. In Knowledgenet, facts are instances of Python classes. Before authoring rules, you need to define the fact classes that represent the data in your domain.

### Basic Fact Classes
A fact class is a standard Python class. At minimum, it should have an `__init__` method and, for debugging purposes, `__str__` and `__repr__` methods:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __str__(self):
        return f"Person({self.name}, {self.age})"

    def __repr__(self):
        return self.__str__()
```

### Hash and Equality
Facts must be **hashable** because Knowledgenet stores them in sets internally. Python's default object identity (`id()`) satisfies this for most cases. However, if you need facts to be deduplicated based on their content (e.g., two `Person` objects with the same `id` field should be treated as the same fact), you must implement `__hash__` and `__eq__`:

```python
class Person:
    def __init__(self, id, name, age):
        self.id = id
        self.name = name
        self.age = age

    def __eq__(self, other):
        if isinstance(other, Person):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return f"Person({self.id}, {self.name})"

    def __repr__(self):
        return self.__str__()
```

### Using Pydantic Models
For more structured fact definitions, you can use Pydantic `BaseModel` classes. This provides automatic validation and serialization:

```python
from pydantic import BaseModel, Field
from typing import Any

class Driver(BaseModel):
    id: str = Field(..., description="Unique driver identifier")
    name: str = Field(..., description="Driver full name")
    age: int = Field(..., description="Driver age")

    def __eq__(self, obj: Any) -> bool:
        if isinstance(obj, Driver):
            return self.id == obj.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return f'Driver({self.id})'

    def __repr__(self) -> str:
        return self.__str__()
```

### Built-in Python Types as Facts
Facts can also be instances of Python built-in types, as long as they are hashable. For example, `tuple`, `frozenset`, `int`, `str`, and `float` can all be used as facts directly:

```python
facts = [("key", "value"), frozenset([1, 2, 3]), 42]
result = service.execute(facts)
```

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
Let's start with a simple rule that classifies a person as a minor or adult based on age:

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

### Running a Rule
To execute a rule, you need a `Service`, a `Repository`, and a `Ruleset`:

```python
from knowledgenet.service import Service
from knowledgenet.repository import Repository
from knowledgenet.ruleset import Ruleset

# Create the ruleset and repository
repo = Repository('my-repo', [
    Ruleset('classification', [rule])
])

# Create the service
service = Service(repo)

# Execute with input facts
input_facts = [Person('Alice', 15), Person('Bob', 30)]
result_facts = service.execute(input_facts)

# Inspect results
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
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

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
Instead of matching by Python type, you can match facts by a string name. This is useful for configuration or context facts that don't warrant a full class definition. Named facts are created using the `Wrapper` class:

```python
from knowledgenet.ftypes import Wrapper

# Create a named fact
config = Wrapper(named='app-config', max_retries=3, timeout=30)

# Match it in a rule
rule = Rule(
    when=Fact(named='app-config', var='config'),
    then=lambda ctx: print(f"Max retries: {ctx.config.max_retries}")
)
```

Named facts are commonly used in the auto-insurance example to pass ruleset-level context:

```python
# Inserted as input fact
context_fact = Wrapper(named='validation-ruleset', description='Validation phase')

# Matched in rules
rule = Rule(
    when=[
        Fact(named='validation-ruleset', var='ruleset_context'),
        Fact(of_type=Request, var='request',
             matches=lambda ctx, this: not this.policy)
    ],
    then=lambda ctx: insert(ctx, create_action(ctx, ctx.ruleset_context, ctx.request))
)
```

### The Wrapper Class
The `Wrapper` class provides a flexible way to create facts without defining dedicated classes. It supports three creation patterns:

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
For complex logic, define a separate function:

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

# In a match expression
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
```

#### session(ctx) -> Session
Returns the current `Session` object:

```python
from knowledgenet.helper import session

current_session = session(ctx)
```

#### global_ctx(ctx) -> dict
Returns the global context dictionary shared across all rule executions within a service. This is set when creating the `Service`:

```python
service = Service(repo, global_ctx={'db_connection': conn, 'api_key': key})

# In a rule's then clause:
from knowledgenet.helper import global_ctx

def lookup_data(ctx):
    conn = global_ctx(ctx)['db_connection']
    # use conn to query external data
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

repo = Repository('pipeline', [Ruleset('rs', [rule_validate, rule_process])])
result = Service(repo).execute([RawData(42)])
# result contains: RawData(42), ValidatedData(...), ProcessedResult(...)
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

# Rule 2: Set value to zero (fires first because of order)
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

# With 2 persons and 3 cities, this creates 2 × 3 = 6 nodes
facts = [Person('Alice', 25), Person('Bob', 30),
         City('NYC'), City('LA'), City('Chicago')]
result = Service(Repository('r', [Ruleset('rs', [rule])])).execute(facts)
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
A `Collector` is a special fact type that automatically aggregates facts of a specified type. To use collectors, you:
1. Create a `Collector` fact and include it in the input facts (or insert it from a rule)
2. Write rules that match the collector using `Collection` or `Fact(of_type=Collector, group=...)`

```python
from knowledgenet.container import Collector
from knowledgenet.rule import Rule, Fact, Collection

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

# Execute with a collector and items
facts = [
    OrderItem('Widget', 50, 2),
    OrderItem('Gadget', 75, 1),
    Collector(of_type=OrderItem, group='order_items',
              value=lambda item: item.price * item.quantity)
]
result = Service(Repository('r', [Ruleset('rs', [rule])])).execute(facts)
```

### Collector Parameters
The `Collector` constructor accepts:

| Parameter | Description |
|-----------|-------------|
| `group` | A unique string identifier for this collector |
| `of_type` | The fact type to collect |
| `filter` | Optional function(s) to filter which facts are collected. Receives `(collector, fact)` as arguments |
| `value` | Optional function to extract a numeric value from each fact. Required for `sum()` and `variance()` |
| `key` | Optional function to extract a comparison key from each fact. Required for `minimum()` and `maximum()` |
| `**kwargs` | Additional keyword arguments are stored as attributes on the collector |

### Collector Aggregate Methods

| Method | Description | Requires |
|--------|-------------|----------|
| `sum()` | Sum of all collected values | `value` parameter |
| `variance()` | Statistical variance of collected values | `value` parameter |
| `minimum()` | Fact with the minimum key | `key` parameter |
| `maximum()` | Fact with the maximum key | `key` parameter |
| `size()` | Number of collected facts | - |
| `empty()` | `True` if no facts collected | - |
| `collection` | The set of collected fact objects | - |

### Collector with Filter
You can filter which facts are added to a collector:

```python
# Only collect items with price > 10
collector = Collector(
    of_type=OrderItem,
    group='expensive_items',
    filter=lambda collector, item: item.price > 10,
    value=lambda item: item.price
)
```

The filter function receives the collector instance as the first argument and the candidate fact as the second. This allows filters that reference collector attributes:

```python
# Collector that only collects items belonging to a specific parent
collector = Collector(
    of_type=OrderItem,
    group='order_items',
    parent=some_order,  # Custom attribute stored on collector
    filter=lambda collector, item: item.order_id == collector.parent.id,
    value=lambda item: item.price
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

### Collection Syntax
The `Collection` class is syntactic sugar for `Fact(of_type=Collector, group=...)`:

```python
# These are equivalent:
Collection(group='my_group', matches=lambda ctx, this: this.sum() > 10)
Fact(of_type=Collector, group='my_group', matches=lambda ctx, this: this.sum() > 10)
```

Using `Collection` is recommended for clarity.

### Automatic Collector Updates
Collectors automatically update when facts are inserted, updated, or deleted during rule execution. When a collector's contents change, rules that depend on it are re-evaluated:

```python
rule_add_item = Rule(
    id='add_bonus_item',
    when=Fact(of_type=Order, var='order',
              matches=lambda ctx, this: this.qualifies_for_bonus),
    then=lambda ctx: insert(ctx, OrderItem('Bonus', 0, 1))
)

# This rule automatically re-evaluates when the new OrderItem is added
rule_check_total = Rule(
    id='check_total', order=1,
    when=Collection(group='order_items', var='items'),
    then=lambda ctx: insert(ctx, Summary(ctx.items.sum(), ctx.items.size()))
)
```

## Events
Events allow rules to react to changes in the FactSet (insertions, updates, and deletions of specific fact types) rather than matching individual facts.

### EventFact
An `EventFact` monitors one or more fact types for changes. It is included in the input facts:

```python
from knowledgenet.ftypes import EventFact
from knowledgenet.rule import Event

# Monitor changes to OrderItem facts
event = EventFact(group='item-changes', on_types=OrderItem)

# Monitor changes to multiple types
event = EventFact(group='order-changes', on_types=[OrderItem, OrderDiscount])
```

### Event Rules
Use the `Event` condition in the `when` clause to match events:

```python
rule = Rule(
    id='on_item_change',
    when=Event(group='item-changes', var='event'),
    then=lambda ctx: handle_change(ctx, ctx.event)
)
```

The `Event` class is syntactic sugar for `Fact(of_type=EventFact, group=...)`.

### Event Properties
When an event fires, the `EventFact` object provides:

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

### Custom Event Parameters
`EventFact` supports custom keyword arguments stored as attributes:

```python
event1 = EventFact(group='audit-events', on_types=Action, id='audit-1', severity='high')
event2 = EventFact(group='audit-events', on_types=Action, id='audit-2', severity='low')
```

Multiple `EventFact` instances with the same `group` but different parameters are treated as distinct facts, each creating their own node when matched by rules.

## Declarative Rules with @ruledef
The `@ruledef` decorator provides a clean way to define rules in separate Python modules that are automatically discovered and registered.

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

A disabled rule is not registered with the engine. This is useful during development or for conditional feature flags.

### Directory Structure Convention
When using `@ruledef` with automatic repository/ruleset discovery, organize your rules in the following directory structure:

```
rules/
  <repository-name>/
    01_validation/
      validation_rules.py
      field_checks.py
    02_business/
      eligibility_rules.py
      pricing_rules.py
    03_finalization/
      selection_rules.py
```

- Each top-level directory under `rules/` becomes a **repository**
- Each subdirectory becomes a **ruleset**, ordered alphabetically by directory name
- Each `.py` file contains rule definitions decorated with `@ruledef`

Prefixing directory names with numbers (e.g., `01_`, `02_`) ensures the desired execution order since rulesets are sorted alphabetically.

### Loading Declarative Rules

```python
import os
from knowledgenet.scanner import load_rules_from_filepaths, lookup
from knowledgenet.service import Service

def init_service(rules_path):
    # Collect all subdirectory paths
    subdirs = [os.path.join(rules_path, name)
               for name in sorted(os.listdir(rules_path))
               if os.path.isdir(os.path.join(rules_path, name))]

    # Load rules from all subdirectories
    load_rules_from_filepaths(subdirs)

    # Look up the repository and create the service
    repo_name = os.path.basename(rules_path)
    repository = lookup(repo_name)
    return Service(repository)
```

## Rule Execution Order

### The Order Attribute
The `order` attribute controls the relative execution priority of rules within a ruleset. Rules with lower `order` values execute first:

```python
rule_a = Rule(id='first', order=0, when=..., then=...)   # Executes first
rule_b = Rule(id='second', order=1, when=..., then=...)  # Executes second
rule_c = Rule(id='third', order=2, when=..., then=...)   # Executes third
```

The default `order` is `0`. Rules with the same order value have their nodes placed in the graph without a guaranteed relative order.

### Ruleset Ordering
Rulesets within a repository are executed in the order they are defined:

```python
repo = Repository('my-repo', [
    Ruleset('validation', validation_rules),     # Executes first
    Ruleset('business-logic', business_rules),   # Executes second
    Ruleset('pricing', pricing_rules)            # Executes third
])
```

The output facts from one ruleset become the input facts for the next.

### Custom Node Sorting
For advanced use cases, you can provide a custom node sorting function when creating the `Service`:

```python
service = Service(repo, node_sorter=my_custom_sorter)
```

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
- Initialization rules that should fire exactly once per matching fact combination
- Validation rules where you want a single check per request
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

The difference between `run_once` and `retrigger_on_update`:
- `run_once=True`: The node is **permanently removed** from the graph after first execution. It will never fire again for that fact combination.
- `retrigger_on_update=False`: The node **stays in the graph** but its cached evaluation result is not invalidated when its matched facts are updated. It can still fire again if new fact combinations are created (e.g., via insert).

## Flow Control Across Rulesets

### Normal Flow
By default, rulesets execute in sequence. The output of each ruleset feeds into the next:

```
Ruleset 1 → Ruleset 2 → Ruleset 3 → Result
```

### Skipping a Ruleset with next_ruleset()
`next_ruleset(ctx)` terminates the current ruleset and proceeds to the next one. Remaining rules in the current ruleset are skipped:

```python
# If validation fails, skip business rules and go to the next ruleset
rule = Rule(
    id='skip_on_error',
    when=Fact(of_type=ValidationError),
    then=lambda ctx: next_ruleset(ctx)
)
```

### Jumping to a Specific Ruleset with switch()
`switch(ctx, ruleset_id)` terminates the current ruleset and jumps directly to the specified ruleset, skipping any intermediate ones:

```python
repo = Repository('my-repo', [
    Ruleset('rs1', [rule_1]),    # Executing
    Ruleset('rs2', [rule_2]),    # Skipped by switch
    Ruleset('rs3', [rule_3])     # Jump target
])

# In a rule within rs1:
then=lambda ctx: switch(ctx, 'rs3')
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

# Validation ruleset
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

repo = Repository('app', [
    Ruleset('validation', [validate_required, stop_on_error]),
    Ruleset('business', business_rules)  # Skipped if validation fails
])
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

# Aggregation rule
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

facts = [
    Person('Alice', 22),
    DrivingRecord(accidents=1),
    Collector(of_type=Score, group='scores',
              value=lambda s: s.points)
]
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
class AuditEntry:
    def __init__(self, action, fact_type, details):
        self.action = action
        self.fact_type = fact_type
        self.details = details

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

facts = [
    input_fact_1, input_fact_2,
    EventFact(group='audit', on_types=[OrderItem, Payment])
]
```

### Multi-Ruleset Pipeline
Organize complex business logic into distinct phases:

```python
# Directory structure:
# rules/claims/
#   01_validation/
#     field_validation.py
#     business_validation.py
#   02_eligibility/
#     contract_rules.py
#     coverage_rules.py
#   03_fraud/
#     fraud_detection.py
#   04_pricing/
#     pricing_rules.py
#   05_finalization/
#     selection_rules.py

# Each phase operates on the facts produced by the previous phase.
# Validation inserts ValidationError facts if checks fail.
# Eligibility evaluates contract terms.
# Fraud detection flags suspicious claims.
# Pricing computes payment amounts.
# Finalization selects the best action.
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
# PROBLEM: Creates Cartesian product of all persons × all addresses
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
All facts stored in the FactSet must be hashable. If your fact class uses mutable containers as attributes, the default `object.__hash__` (based on `id()`) works fine. But if you override `__eq__`, you must also override `__hash__`:

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

## Tracing and Debugging
Knowledgenet integrates with OpenTelemetry for detailed tracing of rule execution. See the [rules-service documentation](rule-service.md#enable-tracing) for configuration details.

### Enabling Tracing

```python
result = service.execute(facts, trc_level=10, trc_details=5)
```

- `trc_level`: Controls the trace stack depth (0 = disabled, max 20). Values up to 10 are for application-level debugging; higher values are for engine internals.
- `trc_details`: Controls the amount of detail in trace spans (0 = minimal, max 10).

### File-based Tracing
Knowledgenet includes a `FileSpanExporter` for writing trace output to `.ndjson` files, useful during development:

```python
from knowledgenet.core.file_trace_exporter import FileSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry import trace

provider = TracerProvider(resource=Resource.create({"service.name": "my-app"}))
exporter = FileSpanExporter("trace-output.ndjson")
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# Now execute with tracing
with trace.get_tracer(__name__).start_as_current_span("my-transaction"):
    result = service.execute(facts, trc_level=10, trc_details=5)

provider.shutdown()
```

## Testing Rules
Well-tested rules are critical for a reliable system. Here are recommended patterns for unit testing.

### Basic Test Structure

```python
import pytest
from knowledgenet.service import Service
from knowledgenet.repository import Repository
from knowledgenet.ruleset import Ruleset

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

### Testing Rule Chaining

```python
def test_validation_stops_execution():
    rules = [validate_required, stop_on_error]
    business_rule = Rule(id='business',
                         when=Fact(of_type=Request),
                         then=lambda ctx: insert(ctx, Result('processed')))

    repo = Repository('test', [
        Ruleset('validation', rules),
        Ruleset('business', [business_rule])
    ])

    # Request without required field
    result = Service(repo).execute([Request(customer_id=None)])

    errors = find_results(ValidationError, result)
    assert len(errors) == 1

    results = find_results(Result, result)
    assert len(results) == 0  # Business rules were skipped
```

### Testing Collections

```python
def test_aggregate_scoring():
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

## Quick Reference

### Imports

```python
# Rule definition
from knowledgenet.rule import Rule, Fact, Collection, Event

# Fact types
from knowledgenet.container import Collector
from knowledgenet.ftypes import EventFact, Wrapper

# Control functions
from knowledgenet.controls import insert, update, delete, switch, next_ruleset, end

# Helper functions
from knowledgenet.helper import assign, factset, node, session, global_ctx

# Declarative rules
from knowledgenet.decorator import ruledef

# Service infrastructure
from knowledgenet.service import Service
from knowledgenet.repository import Repository
from knowledgenet.ruleset import Ruleset
from knowledgenet.scanner import load_rules_from_filepaths, lookup
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
