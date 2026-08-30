"""Convenience helpers for rule context interaction.

These utilities are intended for use in ``matches`` and ``then`` callables to
improve readability and reduce direct access to private context fields.
"""

from types import SimpleNamespace

from knowledgenet.factset import Factset
from knowledgenet.node import Node
from knowledgenet.core.session import Session

def assign(ctx: SimpleNamespace, **kwargs: object)->bool:
    """Assign values onto the rule context and return True.

    This pattern enables concise match expressions such as
    ``assign(ctx, person=this) and this.age > 21``.
    """
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def global_ctx(ctx:SimpleNamespace)->object:
    """Return service-level global context attached to active session."""
    return ctx._session.global_ctx

def node(ctx:SimpleNamespace)->Node:
    """Return currently executing runtime Node."""
    return ctx._node

def factset(ctx:SimpleNamespace)->Factset:
    """Return current session Factset for ad hoc queries."""
    return ctx._facts

def session(ctx:SimpleNamespace)->Session:
    """Return active session instance."""
    return ctx._session