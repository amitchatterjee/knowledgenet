
class Switch:
    def __init__(self, ruleset:str):
        self.ruleset = ruleset
        
class Collector:
    def __init__(self, id:str, of_type:type, filter:callable=None, nvalue:callable=None):
        self.of_type = of_type
        self.id = id
        self.filter = filter
        self.nvalue = nvalue  
        self.collection = set()
        self.sum = 0.0

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

        if self.nvalue:
            val = self.nvalue(obj)
            self.sum = self.sum + val
        return True

    def remove(self, obj):
        if type(obj) != self.of_type:
            return False
        if obj not in self.collection:
            return False
        if self.filter and not self.filter(obj):
            return False
        
        self.collection.remove(obj)
        if self.nvalue:
            val = self.nvalue(obj)
            self.sum = self.sum - val
        return True
