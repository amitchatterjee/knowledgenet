# Rule Creation in Knowledgenet

## Overview
Rules in Knowledgenet can be created using two approaches:
1. Direct instantiation of `Rule` objects
2. Using the `@ruledef` decorator to declaratively define rules

## Rule Structure
A rule consists of three main components:

1. **Rule Attributes** - Optional properties that control rule behavior:
   - `id`: Unique identifier for the rule
   - `order`: Controls execution priority (lower numbers execute first)
   - `run_once`: If True, the rule only executes once
   - `retrigger_on_update`: Controls whether rule re-executes when facts are updated

2. **When (Conditions)** - Define when the rule should fire:
   - Can specify single or multiple conditions using `Fact` or `Collection`
   - Each condition can include a `matches` lambda/function for filtering
   - Can use `var` parameter to store matched facts in context

3. **Then (Actions)** - Define what happens when conditions are met:
   - Can be a single function or list of functions
   - Functions receive a context object containing matched facts
   - Common actions: `insert()`, `update()`, `delete()`

## Creating Rules Programmatically

Basic rule with single condition:
```python
rule = Rule(
    id='r1',
    when=Fact(of_type=C1, matches=lambda ctx, this: this.val > 1),
    then=lambda ctx: insert(ctx, R1(ctx.val))
)
```

Rule with multiple conditions:
```python
rule = Rule(
    id='r1',
    when=[
        Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this)),
        Fact(of_type=C2, matches=lambda ctx, this: this.val > ctx.c1.val)
    ],
    then=lambda ctx: insert(ctx, R1(ctx.c1, ctx.c2))
)
```

## Declarative Rule Creation

Using the `@ruledef` decorator:
```python
@ruledef()
def rule1():
    return Rule(
        when=Fact(of_type=C1, matches=lambda ctx, this: this.val <= 10),
        then=lambda ctx: insert(ctx, R1(ctx.c1, 'small'))
    )
```

The decorator can include properties:
```python
@ruledef(
    id='custom-id',
    ruleset='custom-ruleset', 
    repository='custom-repo',
    enabled=False
)
def rule1():
    return Rule(...)
```

## Best Practices

1. **Use Meaningful IDs**: Give rules clear, descriptive identifiers

2. **Context Management**: Use the `assign()` helper to store matched facts in context
   ```python
   matches=lambda ctx, this: assign(ctx, fact=this) and this.val > 10
   ```

3. **Complex Actions**: For complex then logic, define separate functions:
   ```python
   def complex_action(ctx):
       # Multiple operations
       ctx.fact.val = new_value
       update(ctx, ctx.fact)
       insert(ctx, NewFact())

   Rule(when=..., then=complex_action)
   ```

4. **Rule Organization**: 
   - Group related rules into rulesets
   - Use order attribute for explicit sequencing
   - Consider using run_once for initialization rules
