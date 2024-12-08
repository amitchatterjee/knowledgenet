from ftypes import Collector

class Factset:
    def __init__(self):
        self.facts = set()
        self.__type_to_facts:dict[type,object] = {}
        self.__type_to_collector:dict[type,Collector] = {}

    def __str__(self):
        return f"Factset({self.facts})"
    
    def __repr__(self):
        return self.__str__()

    def add_facts(self, f):
        new_facts = set(f) - self.facts

        # Initialize the newly-added collectors
        new_collectors = set()
        for collector in new_facts:
            if type(collector) == Collector:
                new_collectors.add(collector)
                self.__add_to_collector_facts_dict(collector)
                # Initialize the newly-added collectors with facts that are already in the factset 
                matching_facts = self.__type_to_facts[collector.of_type]
                for matching_fact in matching_facts:
                    # add all the facts of the same type. The filter and other functions passed to the collector, will decide whether to add it or not 
                    collector.add(matching_fact)

        # Initialize the newly-added facts
        updated_collectors = set()
        for fact in new_facts:
            if type(fact) != Collector:
                self.__add_to_type_facts_dict(fact)

                # If this type of this fact matches one or more collectors that are interested in this type 
                if type(fact) in self.__type_to_collector:
                    matching_collectors = self.__type_to_collector[type(fact)]
                    for collector in matching_collectors:
                        if collector.add(fact):
                            updated_collectors.add(collector)

         # Update the factset
        self.facts.update(new_facts)

        return new_facts, updated_collectors - new_collectors
    
    def del_facts(self, facts):
        updated_collectors = set()
        for fact in facts:
            self.facts.remove(fact)
            typ = type(fact)
            if typ != Collector and typ in self.__type_to_facts:
                flist = self.__type_to_facts[typ]
                flist.remove(fact)
                if type(fact) in self.__type_to_collector:
                    matching_collectors = self.__type_to_collector[type(fact)]
                    for collector in matching_collectors:
                        if collector.remove(fact):
                            updated_collectors.add(collector)
            elif typ == Collector and typ in self.__type_to_collector:
                flist = self.__type_to_collector[typ]
                flist.remove(fact)
        return updated_collectors

    def __add_to_type_facts_dict(self, fact):
        facts_list = self.__type_to_facts[type(fact)] if type(fact) in self.__type_to_facts else set()
        facts_list.add(fact)
        self.__type_to_facts[type(fact)] = facts_list

    def __add_to_collector_facts_dict(self, collector):
        collectors_list = self.__type_to_collector[collector.of_type] if collector.of_type in self.__type_to_collector else set()
        collectors_list.add(collector)
        self.__type_to_collector[collector.of_type] = collectors_list

    def facts_of_type(self, of_type):
        return self.__type_to_facts[of_type] if of_type in self.__type_to_facts else None
