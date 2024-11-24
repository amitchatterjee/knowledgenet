from pyrete.utils import to_list

class Rule:
    def __init__(self, id, whens, thens, rank=0, **kwargs):
        self.id = id
        self.rank = rank
        self.whens = to_list(whens)
        self.thens = to_list(thens)
        for key, value in kwargs.items():
            setattr(self, key, value)
        # TODO add validations

    def __str__(self):
        return f"Rule({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.id == other.name

class When:
    def __init__(self, onclass, exp):
        self.onclass = onclass
        self.exp = exp
        # TODO add validation
