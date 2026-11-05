"""Type stub for the optional compiled backend.

Hand-written: PyO3 doesn't generate one. Extend this alongside lib.rs as real
ported functions land.
"""

from decimal import Decimal
from typing import Any

def backend_name() -> str: ...
def combinations(ll: list[list], include_only: list | None = ...) -> list[list]: ...

class Element:
    # Structurally interchangeable with core.graph.Element (same attribute
    # shape) but not its nominal subtype - callers at the core/graph.py
    # boundary treat values here as Any and cast back to Element.
    prev: Any
    next: Any
    obj: Any
    ordinal: int
    weight: Decimal
    def __init__(self, prev: Any, next: Any, obj: Any, ordinal: int, weight: Decimal) -> None: ...

class OrdinalIndex:
    def __init__(self) -> None: ...
    def add(self, first: Any, obj: Any, ordinal: int) -> tuple[Any, Any]: ...
    def on_delete(self, element: Any, prev: Any) -> None: ...

def add_to_dict_of_sets(d: dict, key: Any, value: Any) -> None: ...
def population(d: dict, key: Any) -> set: ...
