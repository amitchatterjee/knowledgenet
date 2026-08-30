"""Rule authoring DSL primitives.

This module defines typed descriptors for ``when`` clauses and the executable
Rule object consumed by runtime sessions.
"""

from collections.abc import Callable
import uuid

from knowledgenet.ftypes import EventFact
from knowledgenet.util import to_list, to_tuple
from knowledgenet.container import Collector

class Event:
    """Descriptor for event-driven when clauses.

    Event is syntactic sugar that is normalized into ``Fact(of_type=EventFact,
    group=...)`` during Rule construction.

    Example:
        React to changes tracked by an EventFact group::

            Rule(
                when=Event(group='c1-events', var='event'),
                then=lambda ctx: insert(ctx, R1(len(ctx.event.added)))
            )
    """

    def __init__(self, group: str,
                 matches: list[Callable] | tuple[Callable] | Callable = lambda ctx, this: True,
                 var: str | None = None) -> None:
        self.group = group
        self.var = var
        self.matches = matches

class Collection:
    """Descriptor for collector-driven when clauses.

    Collection is syntactic sugar that is normalized into
    ``Fact(of_type=Collector, group=...)`` during Rule construction.

    Example:
        Match a collector and compute aggregates::

            Rule(
                when=Collection(group='sum_of_c1s', var='c'),
                then=lambda ctx: insert(ctx, R1(ctx.c.sum(), ctx.c.size()))
            )
    """

    def __init__(self, group: str,
                 matches: list[Callable] | tuple[Callable] | Callable = lambda ctx, this: True,
                 var: str | None = None) -> None:
        self.group = group
        self.matches = to_tuple(matches)
        self.var = var

class Fact:
    """Descriptor for matching one fact type in a when clause.

    Multiple Fact descriptors in one rule produce combinations of matching
    facts. Each combination becomes a Node candidate for rule evaluation.

    Example:
        Correlate parent and child facts in a two-clause when list::

            Rule(
                when=[
                    Fact(of_type=P1, matches=lambda ctx, this: assign(ctx, parent=this)),
                    Fact(of_type=Ch1, matches=lambda ctx, this: this.parent == ctx.parent),
                ],
                then=lambda ctx: insert(ctx, R1(ctx.parent))
            )
    """

    def __init__(self, of_type: type | str | None = None, named: str | None = None,
                 matches: list[Callable] | tuple[Callable] | Callable = lambda ctx, this: True,
                 group: str | None = None, var: str | None = None, **kwargs: object) -> None:
        if not named and not of_type:
            raise Exception('Either type or named must be specified')
        
        if named and of_type:
            raise Exception('type and named cannot be specified together')
        
        of_type = named if named else of_type

        if of_type in [Collector, EventFact] and not group:
            raise Exception("when of_type is Collector or EventFact, group must be specified")
        self.of_type = of_type
        self.matches = to_tuple(matches)
        self.group = group
        self.var = var
        for key, value in kwargs.items():
            setattr(self, key, value)

class Rule:
    """Executable rule definition.

    A rule includes one or more normalized when descriptors and one or more
    then callables that are executed when every when predicate evaluates True
    for a matched fact combination.

    Examples:
        Insert-based chaining::

            Rule(
                id='r1',
                when=Fact(of_type=P1, var='parent'),
                then=lambda ctx: insert(ctx, Ch1(ctx.parent, 20))
            )

        Update-driven walkback (avoid loops with ``retrigger_on_update=False``)::

            def zero_out(ctx):
                ctx.c1.val = 0
                update(ctx, ctx.c1)

            Rule(
                id='r2',
                retrigger_on_update=False,
                when=Fact(of_type=C1, var='c1'),
                then=zero_out
            )
    """

    def __init__(self, id: str | None = None,
                 when: list[Fact | Collection] | tuple[Fact | Collection, ...] | Fact | Collection = (),
                 then: list[Callable] | tuple[Callable] | Callable = lambda ctx: None,
                 order: int = 0,
                 run_once: bool = False, retrigger_on_update: bool = True, **kwargs: object) -> None:
        self.id = id if id else uuid.uuid4()
        self.order = order
        self.whens = self._preprocess_whens(when)
        self.thens = to_tuple(then)
        self.run_once = run_once
        self.retrigger_on_update = retrigger_on_update
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _preprocess_whens(self, whens: list[Fact | Collection] | tuple[Fact | Collection, ...] | Fact | Collection) -> tuple[Fact, ...]:
        whens_list = to_list(whens)
        for i, when in enumerate(whens_list):
            if type(when) == Collection:
                whens_list[i] = Fact(of_type=Collector, group=when.group, matches=when.matches, var=when.var)
            elif type(when) == Event:
                whens_list[i] = Fact(of_type=EventFact, group=when.group, matches=when.matches, var=when.var)
            elif type(when) != Fact:
                raise Exception('When clause must only contain Fact, Event and Collection types')
        return to_tuple(whens_list)

    def __str__(self) -> str:
        return f"Rule({self.id}, order:{self.order})"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rule):
            return NotImplemented
        return self.id == other.id
