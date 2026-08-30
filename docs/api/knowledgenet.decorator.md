# knowledgenet.decorator module

Decorator helpers for declarative rule registration.

The `ruledef` decorator marks rule factory functions so scanner discovery can
identify, execute, and register them in the global registry.

### knowledgenet.decorator.ruledef(\*decorator_args: Any, \*\*decorator_kwargs: Any) → Callable

Decorate a function that returns a Rule and register it in the global registry.

The wrapped function is executed by scanners during discovery. Repository and
ruleset metadata can be inferred from file paths or overridden explicitly.

Common overrides include `id`, `ruleset`, `repository`, and
`enabled=False` to skip registration.

### Example

Declare a rule in a module scanned by `load_rules_from_filepaths`:

```default
@ruledef
def classify_minor():
    return Rule(
        when=Fact(of_type=Person, var='person', matches=lambda ctx, this: this.age < 21),
        then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
    )
```
