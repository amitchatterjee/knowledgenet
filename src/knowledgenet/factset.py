import logging
from typing import Union
from knowledgenet.container import Collector
from knowledgenet.ftypes import EventFact
from knowledgenet.tracer import trace
from knowledgenet.util import of_type

class Factset:
    def __init__(self):
        self.facts = set()
        self._init_dictionaries()

    def _init_dictionaries(self):
        self._type_to_facts:dict[Union[type,str],set[object]] = {}

        self._type_to_collectors:dict[type,set[Collector]] = {}
        self._group_to_collectors:dict[str,set[Collector]] = {}

        self._group_to_events:dict[frozenset[type],set[EventFact]] = {}
        self._type_to_events:dict[type,set[EventFact]] = {}

    def __str__(self):
        return f"Factset({self.facts})"
    
    def __repr__(self):
        return self.__str__()
    
    # TODO - In order to support polymorphism in conditions, we need to not only add the fact type to type_to_facts dictionary, but also all the base classes. I need to think through this a bit more.
    def _get_class_hierarchy(self, typ):
        """Gets the class hierarchy for a given type."""
        hierarchy = []
        while typ:
            hierarchy.append(typ)
            typ = typ.__base__
        return hierarchy

    @trace()
    def add_facts(self, f):
        # Dedup
        new_facts = set(f) - self.facts
        
        new_collectors = set()
        # Handle addition of a collector facts first. The next loop may use the collectors added here
        for fact in new_facts:
            if of_type(fact) == Collector:
                new_collectors.add(fact)
                self._add_to_type_collectors_dict(fact)
                self.add_to_group_collectors_dict(fact)
                # Initialize the newly-added collectors with facts that are already in the factset 
                if fact.of_type in self._type_to_facts:
                    matching_facts = self._type_to_facts[fact.of_type]
                    for matching_fact in matching_facts:
                        # add all the facts of the same type. The filter and other functions passed to the collector, will decide whether to add it or not
                        fact.add(matching_fact)

        # Initialize the newly-added facts
        updated_facts = set()

        # Handle addition of a Event facts next. The next loop may use the facts added here
        for fact in new_facts:
            if of_type(fact) == EventFact:
                self._add_to_group_events_dict(fact)
                self._add_to_type_events_dict(fact)
                continue

        for fact in new_facts:
            if of_type(fact) in (EventFact,Collector):
                # Handled above, skip
                continue

            # Handle application-defined facts
            self._add_to_type_facts_dict(fact)
            # If this type of this fact matches one or more collectors that are interested in this type 
            if of_type(fact) in self._type_to_collectors:
                matching_collectors = self._type_to_collectors[of_type(fact)]
                for collector in matching_collectors:
                    if collector.add(fact):
                        updated_facts.add(collector)

            # If this type of this fact matches one or more events that are interested in this type 
            if of_type(fact) in self._type_to_events:
                for event in self._type_to_events[of_type(fact)]:
                    event.added.add(fact)
                updated_facts.update(self._type_to_events[of_type(fact)])

         # Update the factset
        self.facts.update(new_facts)
        return new_facts, updated_facts - new_collectors
    
    @trace()
    def update_facts(self, facts):
        updated_facts = set()
        for fact in facts:
            typ = of_type(fact)
            if typ == Collector:
                continue

            if type == EventFact:
                continue

            # For application-defined facts
            if typ in self._type_to_collectors:
                matching_collectors = self._type_to_collectors[typ]
                for collector in matching_collectors:
                    if fact in collector.collection and collector.value:
                        collector.reset_cache()
                    updated_facts.add(collector)
            if typ in self._type_to_events:
                matching_events = self._type_to_events[typ]
                for event_fact in matching_events:
                    event_fact.updated.add(fact)
                    updated_facts.add(event_fact)
        return updated_facts

    @trace()
    def del_facts(self, facts):
        updated_facts = set()
        for fact in facts:
            if fact not in facts:
                logging.warning("Fact: %s not found", fact)
                continue

            self.facts.remove(fact)
            typ = of_type(fact)

            if typ == Collector:
                if fact in self._group_to_collectors[fact.group]:
                    self._group_to_collectors[fact.group].remove(fact)
                for collectors in self._type_to_collectors.values():
                    if fact in collectors:
                        collectors.remove(fact)
                continue

            if typ == EventFact:
                if fact in self._group_to_events[fact.group]:
                    self._group_to_events[fact.group].remove(fact)
                for events in self._type_to_events.values():
                    if fact in events:
                        events.remove(fact)
                continue
            
            # For application-defined facts
            flist = self._type_to_facts[typ]
            flist.remove(fact)
            typ = of_type(fact)
            if typ in self._type_to_collectors:
                matching_collectors = self._type_to_collectors[typ]
                for collector in matching_collectors:
                    if collector.remove(fact):
                        # If the fact matched the filter and other criteria
                        updated_facts.add(collector)
            if typ in self._type_to_events:
                for event in self._type_to_events[typ]:
                    event.deleted.add(fact)
                updated_facts.update(self._type_to_events[typ])
        return updated_facts

    def _add_to_type_facts_dict(self, fact):
        facts_list = self._type_to_facts[of_type(fact)] \
            if of_type(fact) in self._type_to_facts else set()
        facts_list.add(fact)
        self._type_to_facts[of_type(fact)] = facts_list

    def _add_to_type_collectors_dict(self, collector):
        collectors_list = self._type_to_collectors[collector.of_type] \
            if collector.of_type in self._type_to_collectors else set()
        collectors_list.add(collector)
        self._type_to_collectors[collector.of_type] = collectors_list

    def add_to_group_collectors_dict(self, fact):
        cset = self._group_to_collectors[fact.group] if fact.group in self._group_to_collectors else set()
        cset.add(fact)
        self._group_to_collectors[fact.group] = cset

    def _add_to_group_events_dict(self, event):
        events_list = self._group_to_events[event.group] \
            if event.group in self._group_to_events else set()
        events_list.add(event)
        self._group_to_events[event.group] = events_list

    def _add_to_type_events_dict(self, event_fact):
        for typ in event_fact.on_types:
            events_list = self._type_to_events[typ] \
                if typ in self._type_to_events else set()
            events_list.add(event_fact)
            self._type_to_events[typ] = events_list

    @trace()
    def find(self, of_type, group=None, filter=lambda obj:True, on_types=None):
        if of_type == Collector:
            return {each for each in self._group_to_collectors[group] if filter(each)} \
                if group in self._group_to_collectors else set()
        
        if of_type == EventFact:
            return {each for each in self._group_to_events[group] if filter(each)}\
                if group in self._group_to_events else set()
        
        return {each for each in self._type_to_facts[of_type] if filter(each)} \
            if of_type in self._type_to_facts else set()
