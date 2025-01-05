from typing import Union
import uuid

from knowledgenet.util import to_list, to_tuple
from knowledgenet.collector import Collector

class Wrapper:
    # TODO - implement a wrapper engine and support for this class.
    '''Wrapper class for Facts. When dealing with large fact objects - having all the large facts in memory may not be a viable option. To deal with this problem, we can use a wrapper. The wrapper stores a uniqueue id only instead of the whole object. The wrapper engine associated with the rule engine will be responsible for fetching and writing the object when needed.
    '''
    def __init__(self, of_type:type, id:str, matches:Union[list[callable],tuple[callable],callable]=lambda ctx,this:True, var:str=None):
        self.of_type = of_type
        self.id = id
        self.matches = to_tuple(matches)
        self.var = var

    def __str__(self):
        return str(self.id)
    
    def __repr__(self):
        return self.__str__()

class Collection:
    def __init__(self, group:str, matches:Union[list[callable],tuple[callable],callable]=lambda ctx,this:True, var:str=None):
        self.group = group
        self.matches = to_tuple(matches)
        self.var = var

class Fact:
    def __init__(self, of_type:type, matches:Union[list[callable],tuple[callable],callable]=lambda ctx,this:True, group=None, var:str=None):
        if of_type == Collector and not group:
            raise Exception("when of_type is Collector, group must be specified")
        self.of_type = of_type
        self.matches = to_tuple(matches)
        self.group = group
        self.var = var

class Rule:
    def __init__(self, id:str=None, 
                 when:Union[list[Union[Fact,Collection]],tuple[Union[Fact,Collection]],Union[Fact, Collection]]=(), 
                 then:Union[list[callable],tuple[callable],callable]=lambda ctx: None, 
                 order=0, merges:list[type]=None, 
                 run_once=False, retrigger_on_update=True, **kwargs):
        self.id = id if id else uuid.uuid4()
        self.order = order
        self.merges = merges
        self.whens = self._preprocess_whens(when)
        self.thens = to_tuple(then)
        self.run_once = run_once
        self.retrigger_on_update = retrigger_on_update
        # The following properties are for external rule management entities like scanner, etc.
        for key,value in kwargs.items():
            setattr(self, key, value)

        self.ordinal = 0

    def _preprocess_whens(self, whens):
        whens = to_list(whens)
        for i, when in enumerate(whens):
            if type(when) == Collection:
                whens[i] = Fact(of_type=Collector, group=when.group, matches=when.matches, var=when.var)
            elif type(when) != Fact:
                raise Exception('When clause must only contain Fact and Collection types')
        return to_tuple(whens) 

    def __str__(self):
        return f"Rule({self.id}, order:{self.order})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name
