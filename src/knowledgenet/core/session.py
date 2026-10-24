import logging
from typing import Any, cast
from collections.abc import Callable, Hashable

from knowledgenet.ftypes import EventFact, Wrapper
from knowledgenet.core.tracer import trace
from knowledgenet.core.perm import combinations
from knowledgenet.node import Node
from knowledgenet.factset import Factset
from knowledgenet.core.graph import Graph, Element
from knowledgenet.container import Collector
from knowledgenet.rule import Rule
from knowledgenet.ruleset import Ruleset
from knowledgenet.util import of_type

class Session:
    def __init__(self, ruleset:Ruleset, facts: set|list, id: str, global_ctx: dict[str, object] | None = None, node_sorter: Callable[[Node, Node], int] | None = None) -> None:
        if global_ctx is None:
            global_ctx = {}
        self.id = id
        self.ruleset = ruleset
        # Explicit annotation: Ruleset.rules is `tuple` (via util.to_tuple's
        # untyped return), which otherwise erases to tuple[Any, ...] here and
        # silently turns off checking on every `for rule in self.rules`/
        # `for when in rule.whens` loop in this class (Any is compatible with
        # anything, so mismatched args would pass mypy without this).
        self.rules: tuple[Rule, ...] = ruleset.rules
        self.global_ctx = global_ctx
        self.input_facts = facts
        self.node_sorter = node_sorter

    def __str__(self) -> str:
        return f"Session({self.id})"

    def __repr__(self) -> str:
        return self.__str__()

    @trace()
    def execute(self) -> set:
        self.output_facts = Factset()
        self.graph = Graph(id=self.id, comparator=cast(Callable[[Hashable, Hashable], int] | None, self.node_sorter))
        # Reverse index: fact -> the graph Elements whose node.when_objs
        # references it. Lets _update_facts/_delete_facts find only the nodes
        # a changed fact could actually affect, instead of scanning every
        # node currently in the graph.
        self._fact_to_elements: dict[Hashable, set[Element]] = {}
        # Reverse index: (when.of_type, when.group) -> the rules with a when
        # clause keyed that way. self.rules/their whens are fixed for the
        # life of the session, so this is built once. Lets _add_facts skip
        # rules that have no when clause any of the newly-inserted facts
        # could possibly match, instead of querying Factset.find() for every
        # when clause of every rule on every call.
        self._rules_by_when_key = self._build_rules_by_when_key()
        logging.debug("%s: Initializing graph", self)
        leftmost,_, updated_facts = self._add_facts(self.input_facts)
        logging.debug("%s: Executing rules on graph", self)

        self.graph.new_cursor(element=leftmost)
        while element := self.graph.next_element():
            #print(f"Graph content: {self.graph.to_element_list(cursor_name='list')}")
            node = cast(Node, element.obj)
            # Execute the rule on the node
            result = node.execute(self.output_facts)
            if node.rule.run_once:
                self._deindex_node(element)
                e = self.graph.delete_element(element)
                if element == leftmost:
                    leftmost = e
                element = e

            if result:
                # node.execute() only returns True after setting node.changes.
                assert node.changes is not None
                # If the rule execution resulted in merges (insert, update, delete)
                all_updates = set()

                # The delete objects need to be handled first because the application may decided to delete a fact and then insert the same fact 
                if 'delete' in node.changes:
                    deleted_facts = node.changes['delete']
                    leftmost, deleted, updated_facts =  self._delete_facts(deleted_facts, leftmost)
                    all_updates.update(updated_facts)
                    logging.debug("%s: Deleted facts: %s", self, deleted)

                if 'insert' in node.changes:
                    new_facts = node.changes['insert']
                    leftmost, _, updated_facts = self._add_facts(new_facts, leftmost)
                    all_updates.update(updated_facts)
                    logging.debug("%s: Inserted facts: %s", self, new_facts)

                if 'update' in node.changes:
                    all_updates.update(node.changes['update'])

                if len(all_updates):
                    leftmost, _ = self._update_facts(node, all_updates, leftmost)
                    logging.debug("%s: Updated facts: %s", self, all_updates)

                if 'break' in node.changes:
                    logging.debug("%s: Breaking session: destination: next_ruleset", self)
                    break
                    
                if 'switch' in node.changes:
                    # Terminate the session execution
                    logging.debug("%s: Ending session: destination: %s", self, node.changes['switch'])
                    self.output_facts.add_facts([node.changes['switch']])
                    break

                logging.debug("%s: After all merges were completed: leftmost changed element: %s, current element: %s", self, leftmost, element)

                if element is not leftmost:
                    self.graph.new_cursor(element=leftmost)
        return self.output_facts.facts
    
    @trace(level=11)
    def _delete_facts(self, deleted_facts: set|list, current_leftmost: Element)->tuple[Element|None, set, Any]:
        deduped_deletes = set(deleted_facts)
        changed_collectors = self.output_facts.del_facts(deduped_deletes)
        logging.debug("%s: Finding nodes affected by deleted facts: %s", self, deduped_deletes)
        affected_elements: set[Element] = set()
        for fact in deduped_deletes:
            affected_elements.update(self._fact_to_elements.get(fact, ()))
        # Process in graph (weight) order, not index/set-iteration order: the
        # "jump to successor" branch below is only correct if, by the time we
        # check whether the element being deleted is the current new_leftmost,
        # every earlier-in-the-graph deletion has already been applied -
        # exactly what the original full-scan cursor walk did implicitly.
        new_leftmost: Element | None = current_leftmost
        for element in sorted(affected_elements, key=lambda e: e.weight):
            next_element = self.graph.delete_element(element)
            self._deindex_node(element)
            if new_leftmost is not None and element.obj == new_leftmost.obj:
                # If the leftmost object is being deleted
                new_leftmost = next_element
            else:
                new_leftmost = self._minimum(new_leftmost, element)

        logging.debug("%s: Deleted facts from graph, count: %d, changed_collectors: %s, new leftmost: %s", self, len(deduped_deletes), changed_collectors, new_leftmost)
        return new_leftmost, deduped_deletes, changed_collectors

    @trace(level=11)
    def _update_facts(self, execution_node: Node, facts: set|list,
                       current_leftmost: Element)->tuple[Element, set]:
        deduped_updates = set(facts) # Remove duplicates
        updated_facts = self.output_facts.update_facts(deduped_updates)
        new_leftmost = current_leftmost
        logging.debug("%s: Finding nodes affected by updated facts: %s", self, deduped_updates)
        affected_elements: set[Element] = set()
        for fact in deduped_updates:
            affected_elements.update(self._fact_to_elements.get(fact, ()))
        # reset_whens is a no-op for any node not touching deduped_updates, so
        # only visiting the affected elements (instead of every node in the
        # graph) changes nothing observable here - and unlike _delete_facts,
        # nothing here mutates the graph, so the min-reduction below doesn't
        # depend on visiting order.
        for element in affected_elements:
            node = cast(Node, element.obj)
            if node == execution_node and not node.rule.retrigger_on_update:
                # if this node updated the object and the rule option is not to retrigger on updare
                continue

            if node.reset_whens(deduped_updates):
                new_leftmost = self._minimum(new_leftmost, element)

        if len(updated_facts) > 0:
            logging.debug("%s: An update resulted in changes to collectors: %s", self, updated_facts)
            # As a part of updated, additional collectors may have been affected, update the graph accordingly
            # (matches the pre-optimization behavior of using whichever node
            # ends up at the tail of the graph as the next execution_node)
            tail_node = cast(Node, self.graph.last.obj) if self.graph.last else execution_node
            new_leftmost, chg_count = self._update_facts(tail_node, updated_facts, new_leftmost)
        logging.debug("%s: Updated graph, count: %d, updated facts: %s, new leftmost: %s", self, len(deduped_updates), deduped_updates, new_leftmost)
        return new_leftmost, deduped_updates

    def _get_matching_objs(self, rule: Rule) -> list[set] | None:
        when_objs: list[set] = []
        # For each class associated with the when clause, look if object(s) of that type exists. If objects exist for all of the when clauses, then this rule satisfies the need and is ready to be put in the graph
        for when in rule.whens:
            # _population(), not the public find(), since this is purely a
            # read (combinations() below never mutates when_objs) and the
            # result is never exposed outside this method - avoids a
            # pointless O(population) copy on every call.
            if when.of_type in (Collector,EventFact):
                objs = self.output_facts._population(when.of_type, when.group)
            else:
                # Fact.__init__ guarantees of_type is never actually None (it
                # raises unless of_type or named was given, and named also
                # ends up assigned into self.of_type) - but its declared
                # parameter type is `type | str | None`, which mypy carries
                # through to the attribute. Narrowed away in the Collector/
                # EventFact branch above by the `in (Collector, EventFact)`
                # check; needs an explicit cast here since this branch has no
                # such check to narrow on.
                objs = self.output_facts._population(cast('type | str', when.of_type))
            if not objs:
                return None
            when_objs.append(objs)
        return when_objs

    # --- Rule relevance index (.plans/003 Phase 5) --------------------------
    #
    # Problem: _add_facts() (below) used to call _get_matching_objs() - and
    # therefore query Factset for every when clause - on EVERY rule in
    # self.rules, on EVERY call, even when none of that rule's when clauses
    # could possibly match any of the facts just inserted. A rule can only
    # produce a new node when at least one of its when-clause positions
    # ends up holding a fact from new_facts: combinations()'s include_only
    # mechanism (see core/perm.py) guarantees that any combination with NO
    # new-fact position gets dropped. So a rule none of whose when clauses
    # match any type/group present in new_facts is mathematically guaranteed
    # to produce zero nodes for this call - but the old code only discovered
    # that the slow way, by actually running _get_matching_objs()/
    # combinations() and getting nothing back.
    #
    # Fix, mirroring the same incremental-index pattern Phases 3/4 used at
    # the graph/session layer, one layer up at the rule-matching layer:
    # precompute, once per session (rule.whens is fixed for the session's
    # whole lifetime - see _build_rules_by_when_key, called once from
    # execute()), a lookup from "when clause key" -> the rules that have a
    # when clause with that key. _rules_relevant_to(new_facts) then looks up
    # only the handful of keys this batch of new_facts actually touches, and
    # _add_facts uses the result to skip calling _get_matching_objs() for
    # every other rule outright.
    #
    # The "key" for a when clause is (of_type, group) for Collector/
    # EventFact (where group is what actually distinguishes one population
    # from another of the same class - see _get_matching_objs), or just
    # (of_type, None) for a plain Fact when clause (group is meaningless
    # there, so it's normalized away - two Fact(of_type=X) whens must key
    # the same regardless of whatever unrelated group= a rule author might
    # have set). _when_key() computes this consistently on both the rule
    # side (_build_rules_by_when_key) and the fact side (_rules_relevant_to).
    #
    # Measured impact (.plans/003 Phase 5): a real but modest ~10% win at
    # autoins's scale, NOT a structural fix - Service runs one Session per
    # Ruleset, not per Repository, so self.rules here is already just a
    # handful of rules (not the whole ruleset's worth), which caps how much
    # there was to skip in the first place. combinations() itself still has
    # to scan each RELEVANT rule's when-clause populations in full to locate
    # the new elements, which remains the dominant cost at scale.

    def _when_key(self, of_type: type | str, group: str | None) -> tuple[type | str, str | None]:
        return (of_type, group) if of_type in (Collector, EventFact) else (of_type, None)

    def _build_rules_by_when_key(self) -> dict[tuple[type | str, str | None], list[Rule]]:
        index: dict[tuple[type | str, str | None], list[Rule]] = {}
        for rule in self.rules:
            for when in rule.whens:
                # See the cast note in _get_matching_objs: when.of_type's
                # declared type is wider than what Fact.__init__ actually
                # ever leaves it as.
                when_type = cast('type | str', when.of_type)
                index.setdefault(self._when_key(when_type, when.group), []).append(rule)
        return index

    def _rules_relevant_to(self, new_facts: set) -> set:
        # For each newly-inserted fact, compute its own when-clause key
        # (same shape _when_key produces for a rule's when clause: of_type
        # plus group, but only for Collector/EventFact, where fact.group is
        # how the fact identifies which population it belongs to) and look
        # up which rules registered that key. Rule has no __hash__ (its
        # __eq__ is id-based, so Python disables the default hash), so the
        # result is tracked by rule.id rather than in a set[Rule] directly.
        relevant_ids = set()
        for fact in new_facts:
            typ = of_type(fact)
            group = fact.group if typ in (Collector, EventFact) else None
            for rule in self._rules_by_when_key.get(self._when_key(typ, group), ()):
                relevant_ids.add(rule.id)
        return relevant_ids

    @trace(level=11)
    def _add_facts(self, facts: set|list, current_leftmost:Element|None=None)->tuple[Element|None, set, Any]:
        # The new_facts variable contains a (deduped) set
        new_facts,updated_facts = self.output_facts.add_facts(facts)
        # If all the facts are duplicates, then return
        if not new_facts:
            return current_leftmost, new_facts, updated_facts

        new_leftmost = current_leftmost
        logging.debug("%s: Adding to graph, facts: %s", self, new_facts)

        relevant_rule_ids = self._rules_relevant_to(new_facts)
        for rule in self.rules:
            if rule.id not in relevant_rule_ids:
                # No when clause of this rule can match anything in
                # new_facts, so _get_matching_objs/combinations() would be
                # guaranteed to contribute nothing - skip querying Factset.find()
                # for this rule's when clauses entirely rather than paying for
                # that guaranteed-empty result on every _add_facts call.
                continue
            when_objs = self._get_matching_objs(rule)
            if when_objs:
                # Get all the permutations associated with the objects
                perms = combinations(when_objs, new_facts)
                logging.debug("%s: %s, permutations: %s", self, rule, perms)
                # insert to the graph
                for each in perms:
                    node_id = f"{self.id}:{rule.id}:{each}"
                    node = Node(node_id, rule, self, each)
                    element = self.graph.add(node, node.rule.order)
                    self._index_node(element)
                    logging.debug("%s: Added node: %s", self, element)
                    new_leftmost = self._minimum(new_leftmost, element)
        logging.debug("%s: Inserted into graph, count: %d, updated facts: %s, new leftmost: %s", self, len(new_facts), updated_facts, new_leftmost)
        return new_leftmost, new_facts, updated_facts
    
    def _minimum(self, element1:Element|None, element2:Element)->Element:
        if not element1:
            return element2
        min = element2 if self.graph.compare(element1, element2) >= 0 else element1
        return min

    def _index_node(self, element: Element) -> None:
        node = cast(Node, element.obj)
        for fact in node.when_objs:
            self._fact_to_elements.setdefault(fact, set()).add(element)

    def _deindex_node(self, element: Element) -> None:
        node = cast(Node, element.obj)
        for fact in node.when_objs:
            elements = self._fact_to_elements.get(fact)
            if elements is not None:
                elements.discard(element)
                if not elements:
                    del self._fact_to_elements[fact]
