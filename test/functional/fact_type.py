class C1:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return f"C1(val: {self.val})"
    def __repr__(self):
        return self.__str__()

class C2:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return f"C2(val: {self.val})"
    def __repr__(self):
        return self.__str__()
    
class R1:
    def __init__(self, *vals):
        self.vals = vals
    def __str__(self):
        return f"R1(vals: {self.vals})"
    def __repr__(self):
        return self.__str__()
    
class P1:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return f"P1(val: {self.val})"
    def __repr__(self):
        return self.__str__()
    
class Ch1:
    def __init__(self, parent, val):
        self.parent = parent
        self.val = val
    def __str__(self):
        return f"Ch1(val: {self.val})"
    def __repr__(self):
        return self.__str__()