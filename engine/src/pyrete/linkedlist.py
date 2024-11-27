from decimal import Decimal

class TraversingLinkedList:
    def __init__(self, comparator):
        self.first = None
        self.current = None
        self.comparator = comparator

        # Do not change these constants
        self.PREV=0
        self.NEXT=1
        self.OBJ=2
        self.ORD=3

    def __ordinal(self, prev, next):
        p_ordinal = prev[self.ORD] if prev else Decimal(0)
        n_ordinal = next[self.ORD] if next else p_ordinal + Decimal(100)
        return (p_ordinal + n_ordinal) / Decimal(2)

    def insert(self, obj):
        if not self.first:
            # If this is the only item in the list
            # (prev, next, object, ordinal)
            node = [None, None, obj, self.__ordinal(None,None)]
            self.first = node
            return node[self.ORD]
        
        last = self.first
        element = self.first
        while element:
            # Invoke the comparator.
            result = self.comparator(obj, element[self.OBJ])
            if result < 0:
                # The obj needs to be inserted before the element
                prev = element[self.PREV]
                next = element[self.NEXT]
                node = [prev, element, obj, self.__ordinal(prev,element)]
                if prev:
                    prev[self.NEXT] = node
                else:
                    self.first = node
                if next:
                    next[self.PREV] = node
                return node
            last = element
            element = element[self.NEXT]

        # Insert it at the end
        node = [last, None, obj, self.__ordinal(last, None)]
        last[self.NEXT] = node
        return node

    def delete(self, obj):
        element = self.first
        while element:
            if obj == element[self.OBJ]:
                prev = element[self.PREV]
                next = element[self.NEXT]
                if prev:
                    if next:
                        # Removing an element between two elements
                        prev[self.NEXT] = next
                        next[self.PREV] = prev
                    else:
                        # Removing an element that is at the end of the list
                        prev[self.NEXT] = None
                else:
                    if next:
                        # Removing an element that is first in the list
                        next[self.PREV] = None
                        self.first = next
                    else:
                        # Removing the only element from the list
                        self.first = None
                if self.current and element == self.current:
                    # If this element is currently being iterated on, move the pointer forward
                    self.current = next
                return next
            element = element[self.NEXT]
        return None

    def start(self, node = None):
        if not node:
            self.current = self.first
        else:
            self.current = node

    def get_current(self):
        return self.current[self.ORD] if self.current else None

    def next(self):
        current = self.current if self.current else None
        if not current:
            return None
        self.current = self.current[self.NEXT]
        return current[self.OBJ]
    
    def is_left_of(self, node):
        return self.current[self.ORD] < node[self.ORD]
    
    def is_right_of(self, node):
        return self.current[self.ORD] > node[self.ORD]
    
    def is_on_node(self, node):
        return self.current[self.ORD] == node[self.ORD]