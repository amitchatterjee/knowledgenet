class TraversingLinkedList:
    def __init__(self, comparator):
        self.first = None
        self.current = None
        self.comparator = comparator

        self.obj_lookup = {}

        # Do not change these constants
        self.__PREV=0
        self.__NEXT=1
        self.__OBJ=2
        self.__ORD=3

    def __ordinal(self, prev, next):
        p_ordinal = prev[self.__ORD] if prev else 0
        n_ordinal = next[self.__ORD] if next else p_ordinal + 1000000
        return (p_ordinal + n_ordinal) // 2

    def insert(self, obj):
        if not self.first:
            # If this is the only item in the list
            # (prev, next, object, ordinal)
            node = [None, None, obj, self.__ordinal(None,None)]
            self.obj_lookup[node[self.__ORD]] = node
            self.first = node
            return node[self.__ORD]
        
        last = self.first
        element = self.first
        while element:
            # Invoke the comparator.
            result = self.comparator(obj, element[self.__OBJ])
            if result < 0:
                # The obj needs to be inserted before the element
                prev = element[self.__PREV]
                next = element[self.__NEXT]
                node = [prev, element, obj, self.__ordinal(prev,element)]
                self.obj_lookup[node[self.__ORD]] = node
                if prev:
                    prev[self.__NEXT] = node
                else:
                    self.first = node
                if next:
                    next[self.__PREV] = node
                return node[self.__ORD]
            last = element
            element = element[self.__NEXT]

        # Insert it at the end
        node = [last, None, obj, self.__ordinal(last, None)]
        self.obj_lookup[node[self.__ORD]] = node
        last[self.__NEXT] = node
        return node[self.__ORD]

    def delete(self, obj):
        element = self.first
        while element:
            if obj == element[self.__OBJ]:
                prev = element[self.__PREV]
                next = element[self.__NEXT]
                if prev:
                    if next:
                        # Removing an element between two elements
                        prev[self.__NEXT] = next
                        next[self.__PREV] = prev
                    else:
                        # Removing an element that is at the end of the list
                        prev[self.__NEXT] = None
                else:
                    if next:
                        # Removing an element that is first in the list
                        next[self.__PREV] = None
                        self.first = next
                    else:
                        # Removing the only element from the list
                        self.first = None
                if self.current and element == self.current:
                    # If this element is currently being iterated on, move the pointer forward
                    self.current = next
                del self.obj_lookup[element[self.__ORD]]
                return element[self.__ORD]
            element = element[self.__NEXT]
        return None

    def size(self):
        return len(self.obj_lookup)

    def start(self, ordinal = 0):
        if not ordinal:
            self.current = self.first
        else:
            self.current = self.obj_lookup[ordinal]

    def get_current(self):
        return self.current[self.__ORD] if self.current else None

    def next(self):
        current = self.current if self.current else None
        if not current:
            return None
        self.current = self.current[self.__NEXT]
        return current[self.__OBJ]