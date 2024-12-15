from typing import Callable
class Switch:
    def __init__(self, ruleset:str):
        self.ruleset = ruleset
        
class Collector:
    def __init__(self, id:str, of_type:type, filter:Callable=None, nvalue:Callable=None, **kwargs):
        self.of_type = of_type
        self.id = id
        self.filter = filter
        self.nvalue = nvalue
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.collection = set()
        self.__cached_sum = None

    def __str__(self):
        return f"Collector({self.id}, size:{len(self.collection)})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
      return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

    def add(self, obj):
        if type(obj) != self.of_type:
            return False
        if obj in self.collection:
            return False
        if self.filter and not self.filter(obj):
            return False
        
        self.collection.add(obj)
        self.__cached_sum = None
        return True

    def remove(self, obj):
        if type(obj) != self.of_type:
            return False
        if obj not in self.collection:
            return False
        if self.filter and not self.filter(obj):
            return False
        
        self.collection.remove(obj)
        self.__cached_sum = None
        return True
    
    def sum(self):
        if not self.nvalue:
            raise Exception("Don't know how to compute sum as nvalue is not provided")
        if self.__cached_sum is None:
            self.__cached_sum = sum([self.nvalue(each) for each in self.collection])
        return self.__cached_sum
        
