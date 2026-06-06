# knowledgenet.rule module

Rule authoring DSL primitives.

This module defines typed descriptors for `when` clauses and the executable
Rule object consumed by runtime sessions.

### *class* knowledgenet.rule.Collection(group: str, matches: list[Callable] | tuple[Callable] | Callable = <function Collection.<lambda>>, var: str | None = None)

Bases: `object`

Descriptor for collector-driven when clauses.

Collection is syntactic sugar that is normalized into
`Fact(of_type=Collector, group=...)` during Rule construction.

### Example

Match a collector and compute aggregates:

```default
Rule(
    when=Collection(group='sum_of_c1s', var='c'),
    then=lambda ctx: insert(ctx, R1(ctx.c.sum(), ctx.c.size()))
)
```

### *class* knowledgenet.rule.Event(group, matches: list[Callable] | tuple[Callable] | Callable = <function Event.<lambda>>, var: str | None = None)

Bases: `object`

Descriptor for event-driven when clauses.

Event is syntactic sugar that is normalized into `Fact(of_type=EventFact,
group=...)` during Rule construction.

### Example

React to changes tracked by an EventFact group:

```default
Rule(
    when=Event(group='c1-events', var='event'),
    then=lambda ctx: insert(ctx, R1(len(ctx.event.added)))
)
```

### *class* knowledgenet.rule.Fact(of_type: type | str = None, named: str = None, matches: list[Callable] | tuple[Callable] | Callable = <function Fact.<lambda>>, group=None, var: str | None = None, \*\*kwargs)

Bases: `object`

Descriptor for matching one fact type in a when clause.

Multiple Fact descriptors in one rule produce combinations of matching
facts. Each combination becomes a Node candidate for rule evaluation.

### Example

Correlate parent and child facts in a two-clause when list:

```default
Rule(
    when=[
        Fact(of_type=P1, matches=lambda ctx, this: assign(ctx, parent=this)),
        Fact(of_type=Ch1, matches=lambda ctx, this: this.parent == ctx.parent),
    ],
    then=lambda ctx: insert(ctx, R1(ctx.parent))
)
```

### *class* knowledgenet.rule.Rule(id: str | None = None, when: list[[Fact](#knowledgenet.rule.Fact) | [Collection](#knowledgenet.rule.Collection)] | tuple[[Fact](#knowledgenet.rule.Fact) | [Collection](#knowledgenet.rule.Collection)] | [Fact](#knowledgenet.rule.Fact) | [Collection](#knowledgenet.rule.Collection) = (), then: list[Callable] | tuple[Callable] | Callable = <function Rule.<lambda>>, order=0, run_once=False, retrigger_on_update=True, \*\*kwargs)

Bases: `object`

Executable rule definition.

A rule includes one or more normalized when descriptors and one or more
then callables that are executed when every when predicate evaluates True
for a matched fact combination.

### Examples

Insert-based chaining:

```default
Rule(
    id='r1',
    when=Fact(of_type=P1, var='parent'),
    then=lambda ctx: insert(ctx, Ch1(ctx.parent, 20))
)
```

Update-driven walkback (avoid loops with `retrigger_on_update=False`):

```default
def zero_out(ctx):
    ctx.c1.val = 0
    update(ctx, ctx.c1)

Rule(
    id='r2',
    retrigger_on_update=False,
    when=Fact(of_type=C1, var='c1'),
    then=zero_out
)
```
