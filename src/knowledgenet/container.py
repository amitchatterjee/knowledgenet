from typing import Callable, Union
from numbers import Number
import hashlib
import statistics

from knowledgenet.util import of_type, to_tuple
from knowledgenet.tracer import trace

class Collector:
    def __init__(self, group: str, 
                of_type: type | str, 
                filter: list[Callable] | tuple[Callable] | Callable | str = lambda this,child: True, 
                value: Callable | None = None, key: Callable | None = None, 
                **kwargs):
        from knowledgenet.ftypes import EventFact
        if of_type in (Collector, EventFact):
            raise Exception('Nested Collector and Eventfact types are not supported')
        self.of_type = of_type
        self.group = group
        self.filter = to_tuple(filter)
        self.value = value
        self.key = key
        self.init_args = kwargs
        for key,value in kwargs.items(): # type: ignore
            setattr(self, key, value) # type: ignore

        self.collection = set()
        self._cached_sum = None
        self._cached_variance = None
        self._cached_min = None
        self._cached_max = None

        hasher = hashlib.sha256(group.encode())
        for key,value in sorted(kwargs.items()): # type: ignore
            hasher.update(str(key).encode())
            hasher.update(str(value).encode())
        self.__int_hash = int(hasher.hexdigest(), 16)

    def __str__(self):
        return f"Collector({self.group}, args={self.init_args})"
    
    def __repr__(self):
        return self.__str__()
   
    def __hash__(self):
        return self.__int_hash

    def __eq__(self, other):
        if not isinstance(other, Collector):
            return False
        return self.__hash__() == other.__hash__()

    def size(self) -> int:
        return len(self.collection)
    
    def empty(self) -> bool:
        return len(self.collection) == 0

    def reset_cache(self):
        self._cached_sum = None
        self._cached_variance = None
        self._cached_min = None
        self._cached_max = None

    def _filter_obj(self, obj):
        for each_filter in self.filter:
            if not each_filter(self, obj):
                return False
        return True

    @trace()
    def add(self, obj: object) -> bool:
        if of_type(obj) != self.of_type:
            return False
        if obj in self.collection:
            return False
        if not self._filter_obj(obj):
            return False
        
        self.collection.add(obj)
        self.reset_cache()
        return True

    @trace()
    def remove(self, obj: object) -> bool:
        if of_type(obj) != self.of_type:
            return False
        if obj not in self.collection:
            return False
        if not self._filter_obj(obj):
            return False
        
        self.collection.remove(obj)
        self.reset_cache()
        return True
    
    def sum(self) -> Number:
        if self._cached_sum is None:
            if not self.value:
                raise Exception("Don't know how to compute sum as value function is not defined")
            self._cached_sum = sum([self.value(each) for each in self.collection])
        return self._cached_sum

    def variance(self) -> float:
        if self._cached_variance is None:
            if not self.value:
                raise Exception("Don't know how to compute variance as value function is not defined")
            self._cached_variance = statistics.variance([self.value(each) for each in self.collection]) if len(self.collection) >= 2 else 0.0
        return self._cached_variance

    def minimum(self) -> object:
        if self._cached_min is None:
            if not self.key:
                raise Exception("Don't know how to compute min as key function is not defined")
        self._cached_min = min(self.collection, key=self.key)
        return self._cached_min

    def maximum(self) -> object:
        if self._cached_max is None:
            if not self.key:
                raise Exception("Don't know how to compute max as key function is not defined")
            self._cached_max = max(self.collection, key=self.key)
        return self._cached_max
