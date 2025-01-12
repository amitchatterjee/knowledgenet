import logging
from knowledgenet.collector import Collector
from knowledgenet.ftypes import Eval
from knowledgenet.tracer import trace

class Factset:
    def __init__(self):
        self.facts = set()
        self._init_dictionaries()

    def _init_dictionaries(self):
        self._type_to_facts:dict[type,set[object]] = {}

        self._type_to_collectors:dict[type,set[Collector]] = {}
        self._group_to_collectors:dict[str,set[Collector]] = {}

        self._types_to_eval:dict[frozenset[type],Eval] = {}
        self._type_to_evals:dict[type,set[Eval]] = {}

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
            if type(fact) == Collector:
                new_collectors.add(fact)
                self._add_to_collector_facts_dict(fact)
                cset = self._group_to_collectors[fact.group] if fact.group in self._group_to_collectors else set()
                cset.add(fact)
                self._group_to_collectors[fact.group] = cset
                # Initialize the newly-added collectors with facts that are already in the factset 
                if fact.of_type in self._type_to_facts:
                    matching_facts = self._type_to_facts[fact.of_type]
                    for matching_fact in matching_facts:
                        # add all the facts of the same type. The filter and other functions passed to the collector, will decide whether to add it or not
                        fact.add(matching_fact)

        # Initialize the newly-added facts
        updated_facts = set()

        # Handle addition of a Eval facts next. The next loop may use the Evals added here
        for fact in new_facts:
            if type(fact) == Eval:
                self._types_to_eval[fact.of_types] = fact
                self._add_to_type_evals_dict(fact)
                continue

        for fact in new_facts:
            if type(fact) in (Eval,Collector):
                # Handled above, skip
                continue

            # Handle application-defined facts
            self._add_to_type_facts_dict(fact)
            # If this type of this fact matches one or more collectors that are interested in this type 
            if type(fact) in self._type_to_collectors:
                matching_collectors = self._type_to_collectors[type(fact)]
                for collector in matching_collectors:
                    if collector.add(fact):
                        updated_facts.add(collector)

            # If this type of this fact matches one or more evals that are interested in this type 
            if type(fact) in self._type_to_evals:
                updated_facts.update(self._type_to_evals[type(fact)])

         # Update the factset
        self.facts.update(new_facts)
        return new_facts, updated_facts - new_collectors
    
    @trace()
    def update_facts(self, facts):
        updated_facts = set()
        for fact in facts:
            typ = type(fact)
            if typ == Collector:
                continue

            if type == Eval:
                continue

            # For application-defined facts
            if type(fact) in self._type_to_collectors:
                matching_collectors = self._type_to_collectors[type(fact)]
                for collector in matching_collectors:
                    if fact in collector.collection and collector.value:
                        collector.reset_cache()
                    updated_facts.add(collector)
            if type(fact) in self._type_to_evals:
                matching_evals = self._type_to_evals[type(fact)]
                for eval_fact in matching_evals:
                    updated_facts.add(eval_fact)
        return updated_facts

    @trace()
    def del_facts(self, facts):
        updated_facts = set()
        for fact in facts:
            if fact not in facts:
                logging.warning("Fact: %s not found", fact)
                continue

            self.facts.remove(fact)
            typ = type(fact)

            if typ == Collector:
                if fact in self._group_to_collectors[fact.group]:
                    self._group_to_collectors[fact.group].remove(fact)
                for key,value in list(self._type_to_collectors.items()):  # Create a copy to iterate safely
                    if value == fact:
                        del self._type_to_collectors[key]
                continue

            if typ == Eval:
                for key,value in list(self._types_to_eval.items()):  # Create a copy to iterate safely
                    if value == fact:
                        del self._types_to_eval[key]
                for key,value in list(self._type_to_evals.items()):  # Create a copy to iterate safely
                    if value == fact:
                        del self._type_to_evals[key]
                continue
            
            # For application-defined facts
            flist = self._type_to_facts[typ]
            flist.remove(fact)
            typ = type(fact)
            if typ in self._type_to_collectors:
                matching_collectors = self._type_to_collectors[typ]
                for collector in matching_collectors:
                    if collector.remove(fact):
                        # If the fact matched the filter and other criteria
                        updated_facts.add(collector)
            if typ in self._type_to_evals:
                updated_facts.update(self._type_to_evals[typ])
        return updated_facts

    def _add_to_type_facts_dict(self, fact):
        facts_list = self._type_to_facts[type(fact)] \
            if type(fact) in self._type_to_facts else set()
        facts_list.add(fact)
        self._type_to_facts[type(fact)] = facts_list

    def _add_to_collector_facts_dict(self, collector):
        collectors_list = self._type_to_collectors[collector.of_type] \
            if collector.of_type in self._type_to_collectors else set()
        collectors_list.add(collector)
        self._type_to_collectors[collector.of_type] = collectors_list

    def _add_to_type_evals_dict(self, eval_fact):
        for typ in eval_fact.of_types:
            evals_list = self._type_to_evals[typ] \
                if typ in self._type_to_evals else set()
            evals_list.add(eval_fact)
            self._type_to_evals[typ] = evals_list

    @trace()
    def find(self, of_type, group=None, filter=lambda obj:True, of_types=None):
        if of_type == Collector:
            return {each for each in self._group_to_collectors[group] if filter(each)} \
                if group in self._group_to_collectors else set()
        
        if of_type == Eval:
            return {self._types_to_eval[of_types]} \
                if of_types in self._types_to_eval else set()
        
        return {each for each in self._type_to_facts[of_type] if filter(each)} \
            if of_type in self._type_to_facts else set()
