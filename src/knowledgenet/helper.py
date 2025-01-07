from types import SimpleNamespace

from knowledgenet.factset import Factset
from knowledgenet.node import Node
def assign(ctx: SimpleNamespace, **kwargs)->True:
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return True

def global_ctx(ctx:SimpleNamespace)->object:
    return ctx._global

def node(ctx:SimpleNamespace)->Node:
    return ctx._node

def factset(ctx:SimpleNamespace)->Factset:
    return ctx._facts
