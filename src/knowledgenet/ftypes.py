class Switch:
    def __init__(self, ruleset:str):
        self.ruleset = ruleset
    def __str__(self):
        return f"Switch({self.ruleset})"
    def __repr__(self):
        return self.__str__()
