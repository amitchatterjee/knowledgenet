from knowledgenet.collector import Collector
from knowledgenet.tracer import trace

class Factset:
    def __init__(self):
        self.facts = set()
        self._type_to_facts:dict[type,set[object]] = {}
        self._type_to_collectors:dict[type,set[Collector]] = {}
        self._group_to_collectors:dict[str,set[Collector]] = {}

    def __str__(self):
        return f"Factset({self.facts})"
    
    def __repr__(self):
        return self.__str__()

    def get_collectors(self, group:str)->set[Collector]:
        return self._group_to_collectors[group] if group in self._group_to_collectors else None
    
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
        new_facts = set(f) - self.facts
        # Initialize the newly-added collectors
        new_collectors = set()
        for collector in new_facts:
            if type(collector) == Collector:
                new_collectors.add(collector)
                self._add_to_collector_facts_dict(collector)
                cset = self._group_to_collectors[collector.group] if collector.group in self._group_to_collectors else set()
                cset.add(collector)
                self._group_to_collectors[collector.group] = cset
                # Initialize the newly-added collectors with facts that are already in the factset 
                if collector.of_type in self._type_to_facts:
                    matching_facts = self._type_to_facts[collector.of_type]
                    for matching_fact in matching_facts:
                        # add all the facts of the same type. The filter and other functions passed to the collector, will decide whether to add it or not 
                        collector.add(matching_fact)

        # Initialize the newly-added facts
        updated_collectors = set()
        for fact in new_facts:
            if type(fact) != Collector:
                self._add_to_type_facts_dict(fact)

                # If this type of this fact matches one or more collectors that are interested in this type 
                if type(fact) in self._type_to_collectors:
                    matching_collectors = self._type_to_collectors[type(fact)]
                    for collector in matching_collectors:
                        if collector.add(fact):
                            updated_collectors.add(collector)

         # Update the factset
        self.facts.update(new_facts)
        return new_facts, updated_collectors - new_collectors
    
    @trace()
    def update_facts(self, facts):
        collectors = set()
        updated_collectors = set()
        for fact in facts:
            typ = type(fact)
            if typ != Collector:
                if type(fact) in self._type_to_collectors:
                    matching_collectors = self._type_to_collectors[type(fact)]
                    for collector in matching_collectors:
                        if fact in collector.collection and collector.value:
                            # adjust on the fly stats: sum, etc.
                            collector.remove(fact)
                            collector.add(fact)
                        updated_collectors.add(collector)
        return updated_collectors - collectors

    @trace()
    def del_facts(self, facts):
        updated_collectors = set()
        for fact in facts:
            self.facts.remove(fact)
            typ = type(fact)
            if typ != Collector:
                flist = self._type_to_facts[typ]
                flist.remove(fact)
                if type(fact) in self._type_to_collectors:
                    matching_collectors = self._type_to_collectors[type(fact)]
                    for collector in matching_collectors:
                        if collector.remove(fact):
                            updated_collectors.add(collector)
            else:
                flist = self._type_to_collectors[typ]
                flist.remove(fact)
                cset = self._group_to_collectors[fact.group]
                cset.remove(fact)
                if len(cset) == 0:
                    del self._group_to_collectors[fact.group]
        return updated_collectors

    def _add_to_type_facts_dict(self, fact):
        facts_list = self._type_to_facts[type(fact)] if type(fact) in self._type_to_facts else set()
        facts_list.add(fact)
        self._type_to_facts[type(fact)] = facts_list

    def _add_to_collector_facts_dict(self, collector):
        collectors_list = self._type_to_collectors[collector.of_type] if collector.of_type in self._type_to_collectors else set()
        collectors_list.add(collector)
        self._type_to_collectors[collector.of_type] = collectors_list

    @trace()
    def facts_of_type(self, of_type, group=None, filter=lambda obj:True):
        if of_type == Collector:
            return {each for each in self._group_to_collectors[group] if filter(each)} \
                if group in self._group_to_collectors else None
        else:
            return {each for each in self._type_to_facts[of_type] if filter(each)} \
                if of_type in self._type_to_facts else None
