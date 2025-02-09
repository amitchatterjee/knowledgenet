from types import SimpleNamespace

from knowledgenet.factset import Factset
from knowledgenet.node import Node
from knowledgenet.session import Session

def assign(ctx: SimpleNamespace, **kwargs)->bool:
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def global_ctx(ctx:SimpleNamespace)->object:
    return ctx._session.global_ctx

def node(ctx:SimpleNamespace)->Node:
    return ctx._node

def factset(ctx:SimpleNamespace)->Factset:
    return ctx._facts

def session(ctx:SimpleNamespace)->Session:
    return ctx._session