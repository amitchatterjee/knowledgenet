from typing import Callable
from numbers import Number
import hashlib
import statistics

from knowledgenet.tracer import trace

class Switch:
    def __init__(self, ruleset:str):
        self.ruleset = ruleset
    def __str__(self):
        return f"Switch({self.ruleset})"
    def __repr__(self):
        return self.__str__()
        
class Collector:
    def __init__(self, group:str, of_type:type, filter:Callable=None, 
        nvalue:Callable=None, key:Callable=None, **kwargs):
        self.of_type = of_type
        self.group = group
        self.filter = filter
        self.nvalue = nvalue
        self.key = key
        for key,value in kwargs.items():
            setattr(self, key, value)
        self.collection = set()

        self._cached_sum = None
        self._cached_variance = None
        self._cached_min = None
        self._cached_max = None

        hasher = hashlib.sha256(group.encode())
        for key,value in sorted(kwargs.items()):
            hasher.update(str(key).encode())
            hasher.update(str(value).encode())
        self.__int_hash = int(hasher.hexdigest(), 16)

    def __str__(self):
        return f"Collector({self.group})"
    
    def __repr__(self):
        return self.__str__()
   
    def __hash__(self):
        return self.__int_hash

    def _reset_cache(self):
        self._cached_sum = None
        self._cached_variance = None
        self._cached_min = None
        self._cached_max = None

    @trace()
    def add(self, obj:object)->bool:
        if type(obj) != self.of_type:
            return False
        if obj in self.collection:
            return False
        if self.filter and not self.filter(self, obj):
            return False
        
        self.collection.add(obj)
        self._reset_cache()
        return True

    @trace()
    def remove(self, obj:object)->bool:
        if type(obj) != self.of_type:
            return False
        if obj not in self.collection:
            return False
        if self.filter and not self.filter(self, obj):
            return False
        
        self.collection.remove(obj)
        self._reset_cache()
        return True
    
    def sum(self)->Number:
        if self._cached_sum is None:
            if not self.nvalue:
                raise Exception("Don't know how to compute sum as nvalue function is not defined")
            self._cached_sum = sum([self.nvalue(each) for each in self.collection])
        return self._cached_sum

    def variance(self)->Number:
        if self._cached_variance is None:
            if not self.nvalue:
                raise Exception("Don't know how to compute variance as nvalue function is not defined")
            self._cached_variance = statistics.variance([self.nvalue(each) for each in self.collection]) if len(self.collection) >= 2 else 0.0
        return self._cached_variance

    def minimum(self)->object:
        if self._cached_min is None:
            if not self.key:
                raise Exception("Don't know how to compute min as key function is not defined")
        self._cached_min = min(self.collection, key=self.key)
        return self._cached_min

    def maximum(self)->object:
        if self._cached_max is None:
            if not self.key:
                raise Exception("Don't know how to compute min as key function is not defined")
            self._cached_max = max(self.collection, key=self.key)
        return self._cached_max
        
