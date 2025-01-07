from typing import Union

class Switch:
    def __init__(self, ruleset:str):
        self.ruleset = ruleset
    def __str__(self):
        return f"Switch({self.ruleset})"
    def __repr__(self):
        return self.__str__()

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
