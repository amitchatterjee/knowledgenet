from decimal import Decimal
from typing import TypeVar, Callable, Union
from collections.abc import Hashable
import uuid

T = TypeVar('T')
class Element:    
    def __init__(self:T, prev:Union[T,None], next:Union[T,None], obj:Hashable, ord:Decimal):
        self.prev = prev
        self.next = next
        self.obj = obj
        self.ord = ord

    def __str__(self):
        #return f"Element:({self.obj}, prev:{self.prev.obj if self.prev else None}, next:{self.next.obj if self.next else None} ordinal:{self.ord})"
        return f"Element:({self.obj}, ordinal:{self.ord})"
    
    def __repr__(self):
        return self.__str__()

class Graph:
    def __init__(self, comparator:Callable, id=uuid.uuid1()):
        self.first = None
        self.cursors:dict[str,Element] = {}
        self.comparator = comparator
        self.id = id

    def __str__(self):
        return f"Graph({self.id})"
    
    def __repr__(self):
        return self.__str__()

    def __ordinal(self, prev:Union[Element,None], next:Union[Element,None]) -> Decimal:
        p_ordinal = prev.ord if prev else Decimal(0)
        n_ordinal = next.ord if next else p_ordinal + Decimal(100)
        return (p_ordinal + n_ordinal) / Decimal(2)

    def add(self, obj:Hashable)->Element:
        added_element = None
        if not self.first:
            # If this is the only element in the list
            element = Element(None, None, obj, self.__ordinal(None,None))
            self.first = element
            added_element = element
        else:
            last:Union[Element,None] = None
            element:Element = self.first
            while element:
                # Invoke the comparator.
                result = self.comparator(obj, element.obj)
                if result < 0:
                    # The obj needs to be inserted left of the element
                    added_element = self.__insert(obj, element)
                    break
                last = element
                element = element.next

            if not added_element:
                # Insert it at the rightmost side of the list
                added_element = Element(last, None, obj, self.__ordinal(last, None))
                last.next = added_element

        # adjust cursors
        for name,cursor in self.cursors.items():
            if added_element.next == cursor:
                # If the element being added is just before the cursor, adjust it
                self.cursors[name] = added_element

        return added_element

    def __insert(self, obj:Hashable, current:Element)->Element:
        '''
        Insert object to the left of the current element
        '''
        prev = current.prev
        element = Element(prev, current, obj, self.__ordinal(prev,current))
        if prev:
            prev.next = element
        else:
            self.first = element

        current.prev = element
        return element

    def delete(self, obj:Hashable)->tuple[bool,Element]:
        element = self.first
        while element:
            if obj == element.obj:
                next = self.delete_element(element)
                return True, next
            element = element.next
        # Element is not found
        return False, None

    def delete_element(self, element:Element)->Element:
        prev:Element = element.prev
        next:Element = element.next
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

    def new_cursor(self, cursor_name='default', element:Element=None):
        if not element:
            self.cursors[cursor_name] = self.first
        else:
            self.cursors[cursor_name] = element

    def get_cursor(self, cursor_name='default')->Element:
        return self.cursors[cursor_name]

    def next(self, cursor_name='default')->Hashable:
        cursor = self.next_element(cursor_name)
        if not cursor:
            return None
        return cursor.obj
    
    def next_element(self, cursor_name='default')->Union[Element,None]:
        cursor = self.cursors[cursor_name]
        if not cursor:
            return None
        self.cursors[cursor_name] = cursor.next
        return cursor
    
    def compare(self, element1:Element, element2:Element)->int:
        return element1.ord - element2.ord

    def cursor_is_left_of(self, element:Element, cursor_name='default')->bool:
        return self.compare(self.cursors[cursor_name], element) < 0 if self.cursors[cursor_name] else True
        
    def cursor_is_right_of(self, element:Element, cursor_name='default')->bool:
        return self.compare(self.cursors[cursor_name], element) > 0 if self.cursors[cursor_name] else False
    
    def cursor_is_on(self, element:Element, cursor_name='default')->bool:
        return self.compare(self.cursors[cursor_name], element) == 0 if self.cursors[cursor_name] else False

    def to_list(self, cursor_name='default', element:Element=None)->list:
        result = []
        self.new_cursor(cursor_name, element)
        while True:
            obj = self.next(cursor_name)
            if obj is None:
                break
            result.append(obj)
        return result
    
    def to_element_list(self, cursor_name='default', element:Element=None)->list:
        result = []
        self.new_cursor(cursor_name, element)
        while element:= self.next_element(cursor_name):
            result.append(element)
        return result