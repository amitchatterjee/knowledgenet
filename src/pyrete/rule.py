class Rule:
    def __init__(self, name, whens, thens, rank=0, **kwargs):
        self.name = name
        self.rank = rank
        self.whens = whens
        self.thens = thens
        for key, value in kwargs.items():
            setattr(self, key, value)
        # TODO add validations

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.name == other.name

class When:
    def __init__(self, onclass, exp):
        self.onclass = onclass
        self.exp = exp
        # TODO add validation
