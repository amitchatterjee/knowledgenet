class Rule:
    def __init__(self, name, whens, then, rank=0, **kwargs):
        self.name = name
        self.rank = rank
        self.whens = whens
        self.then = then
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
    def __init__(self, clazz, exp):
        self.clazz = clazz
        self.exp = exp
        # TODO add validation
