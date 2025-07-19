from decimal import Decimal
from collections.abc import Hashable

from knowledgenet.core.tracer import trace

class Element:
    def __init__(self, prev: Element | None, next: Element | None, obj: Hashable, ordinal: int, weight: Decimal):
        self.prev = prev
        self.next = next
        self.obj = obj
        self.ordinal = ordinal
        self.weight = weight

    def __str__(self):
        #return f"Element:({self.obj}, prev:{self.prev.obj if self.prev else None}, next:{self.next.obj if self.next else None} weight:{self.ord})"
        return f"Element:({self.obj}, weight:{self.weight})"
    
    def __repr__(self):
        return self.__str__()

class Graph:
    def __init__(self, id):
        self.first = None
        self.cursors: dict[str, Element | None] = {}
        self.id = id

    def __str__(self):
        return f"Graph({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def _weight(self, prev: Element | None, next: Element | None) -> Decimal:
        p_weight = prev.weight if prev else Decimal(0)
        n_weight = next.weight if next else p_weight + Decimal(100)
        return (p_weight + n_weight) / Decimal(2)

    def add(self, obj: Hashable, ordinal: int) -> Element:
        added_element = None
        if not self.first:
            # If this is the only element in the list
            element = Element(None, None, obj, ordinal, self._weight(None,None))
            self.first = element
            added_element = element
        else:
            last: Element | None = None
            element: Element | None = self.first
            while element:
                if ordinal < element.ordinal:
                    # The obj needs to be inserted left of the element
                    added_element = self._insert(obj, ordinal, element)
                    break
                last = element
                element = element.next

            if not added_element:
                # Insert it at the rightmost side of the list
                added_element = Element(last, None, obj, ordinal, self._weight(last, None))
                if last is not None:
                    last.next = added_element

        # adjust cursors
        for name,cursor in self.cursors.items():
            if added_element.next == cursor:
                # If the element being added is just before the cursor, adjust it
                self.cursors[name] = added_element

        return added_element

    def _insert(self, obj: Hashable, ordinal: int, current: Element) -> Element:
        '''
        Insert object to the left of the current element
        '''
        prev = current.prev
        element = Element(prev, current, obj, ordinal, self._weight(prev,current))
        if prev:
            prev.next = element
        else:
            self.first = element

        current.prev = element
        return element

    def delete(self, obj: Hashable) -> tuple[bool, Element | None]:
        element = self.first
        while element:
            if obj == element.obj:
                next = self.delete_element(element)
                return True, next
            element = element.next
        # Element is not found
        return False, None

    def delete_element(self, element: Element) -> Element | None:
        prev: Element | None = element.prev
        next: Element | None = element.next
        if prev:
            if next:
                # Removing an element between two elements
                prev.next = next
                next.prev = prev
            else:
                # Removing an element that is at the end of the list
                prev.next = None
        else:
            if next:
                # Removing an element that at the beginning of the list
                next.prev = None
                self.first = next
            else:
                # Removing the only element from the list
                self.first = None

        for name,cursor in self.cursors.items():
            if element == cursor:
                # If this element is currently being iterated on, move the pointer forward
                self.cursors[name] = next
                
        return next

    def new_cursor(self, cursor_name='default', element: Element | None = None):
        if not element:
            self.cursors[cursor_name] = self.first
        else:
            self.cursors[cursor_name] = element

    def get_cursor(self, cursor_name='default') -> Element | None:
        return self.cursors[cursor_name]

    def next(self, cursor_name='default') -> Hashable:
        return (cursor := self.next_element(cursor_name)) and cursor.obj
    
    @trace(filter=lambda args,kwargs: len(args) < 2 or args[1] == 'default')
    def next_element(self, cursor_name='default') -> Element | None:
        cursor = self.cursors[cursor_name]
        if not cursor:
            return None
        self.cursors[cursor_name] = cursor.next
        return cursor
    
    @trace(filter=lambda args,kwargs: len(args) < 2 or args[1] == 'default')
    def next_elements(self, cursor_name='default') -> list[Element] | None:
        cursors = []
        ordinal = None    
        while cursor := self.cursors[cursor_name]:
            if ordinal is not None and cursor.ordinal != ordinal:
                break
            cursors.append(cursor)
            ordinal = cursor.ordinal
            self.cursors[cursor_name] = cursor.next
        return cursors
    
    def compare(self, element1: Element, element2: Element) -> Decimal:
        return element1.weight - element2.weight

    def cursor_is_left_of(self, element: Element, cursor_name='default') -> bool:
        cursor = self.cursors[cursor_name]
        return self.compare(cursor, element) < 0 if cursor else False
        
    def cursor_is_right_of(self, element: Element, cursor_name='default') -> bool:
        cursor = self.cursors[cursor_name]
        return self.compare(cursor, element) > 0 if cursor else False
    
    def cursor_is_on(self, element: Element, cursor_name='default') -> bool:
        cursor = self.cursors[cursor_name]
        return self.compare(cursor, element) == 0 if cursor else False

    def to_list(self, cursor_name='default', element: Element | None = None) -> list:
        result = []
        self.new_cursor(cursor_name, element)
        while True:
            obj = self.next(cursor_name)
            if obj is None:
                break
            result.append(obj)
        return result
    
    def to_element_list(self, cursor_name='default', element: Element | None = None) -> list:
        result = []
        self.new_cursor(cursor_name, element)
        while element:= self.next_element(cursor_name):
            result.append(element)
        return result