class TraversingLinkedList:
    def __init__(self, comparator):
        self.first = None
        self.current = None
        self.comparator = comparator

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
            self.first = node
            return
        
        last = self.first
        element = self.first
        while element:
            # Invoke the comparator.
            result = self.comparator(obj, element[self.__OBJ])
            if result < 0:
                # The obj needs to be inserted before the element
                prev = element[self.__PREV]
                next = element[self.__NEXT]
                node = [prev, element, obj, self.__ordinal(prev,next)]
                if prev:
                    prev[self.__NEXT] = node
                else:
                    self.first = node
                if next:
                    next[self.__PREV] = node
                return
            last = element
            element = element[self.__NEXT]

        # Insert it at the end
        node = [last, None, obj, self.__ordinal(last, None)]
        last[self.__NEXT] = node

    def start(self):
        self.current = self.first

    def next(self):
        current = self.current if self.current else None
        if not current:
            return None
        self.current = self.current[self.__NEXT]
        return current[self.__OBJ]
    