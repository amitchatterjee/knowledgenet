"""Decorator helpers for declarative rule registration.

The ``ruledef`` decorator marks rule factory functions so scanner discovery can
identify, execute, and register them in the global registry.
"""

from knowledgenet.scanner import registry


import inspect
import os
from functools import wraps

def ruledef(*decorator_args, **decorator_kwargs):
    """Decorate a function that returns a Rule and register it in the global registry.

    The wrapped function is executed by scanners during discovery. Repository and
    ruleset metadata can be inferred from file paths or overridden explicitly.

    Common overrides include ``id``, ``ruleset``, ``repository``, and
    ``enabled=False`` to skip registration.

    Example:
        Declare a rule in a module scanned by ``load_rules_from_filepaths``::

            @ruledef
            def classify_minor():
                return Rule(
                    when=Fact(of_type=Person, var='person', matches=lambda ctx, this: this.age < 21),
                    then=lambda ctx: insert(ctx, Classification(ctx.person, 'minor'))
                )
    """
    def ruledef_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'enabled' in decorator_kwargs and not decorator_kwargs['enabled']:
                return None

            rule = func(*args, **kwargs)

            # Override the rule ruleset and repository ids
            rule.id = decorator_kwargs.get('id', func.__name__)
            rule_path = os.path.dirname(inspect.getfile(func)).replace("/", os.sep).replace("\\", os.sep)
            splits = rule_path.split(os.sep)
            rule.ruleset = decorator_kwargs.get('ruleset', splits[-1])
            rule.repository = decorator_kwargs.get('repository', splits[-2])
            #logging.info(f"Rule: {rule_path}, {rule.id}, {rule.repository}, {rule.ruleset}")

            if rule.repository not in registry:
                registry[rule.repository] = {}
            if rule.ruleset not in registry[rule.repository]:
                registry[rule.repository][rule.ruleset] = []
            if any(existing_rule.id == rule.id for existing_rule in registry[rule.repository][rule.ruleset]):
                raise Exception(f"Rule with id {rule.id} already exists")
            registry[rule.repository][rule.ruleset].append(rule)
            return rule
        # Mark this wrapper explicitly as a rule definition so scanners
        # can reliably detect rule functions without relying on
        # `__wrapped__` (which other decorators may also set via wraps).
        wrapper.__ruledef__ = True
        return wrapper
    if decorator_args and callable(decorator_args[0]):
        # Decorator called without arguments
        #print('without', decorator_args, decorator_kwargs)
        return ruledef_wrapper(decorator_args[0])
    else:
        # Decorator called with arguments
        #print('with', decorator_args, decorator_kwargs)
        return ruledef_wrapper