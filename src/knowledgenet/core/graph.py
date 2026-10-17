import bisect
from decimal import Decimal
from collections.abc import Hashable, Callable

from knowledgenet.core.tracer import trace

class Element:
    def __init__(self, prev: Element | None, next: Element | None, obj: Hashable, ordinal: int, weight: Decimal):
        self.prev = prev
        self.next = next
        self.obj = obj
        self.ordinal = ordinal
        self.weight = weight

    def __str__(self) -> str:
        #return f"Element:({self.obj}, prev:{self.prev.obj if self.prev else None}, next:{self.next.obj if self.next else None} weight:{self.ord})"
        return f"Element:({self.obj}, weight:{self.weight})"

    def __repr__(self) -> str:
        return self.__str__()

class Graph:
    def __init__(self, id: str, comparator: Callable[[Hashable, Hashable], int] | None = None) -> None:
        self.first: Element | None = None
        self.last: Element | None = None
        self.cursors: dict[str, Element | None] = {}
        self.id = id
        self.comparator = comparator
        # Ordinal-based fast path (comparator is None): for each distinct
        # ordinal currently present, the last element of its contiguous run
        # (same-ordinal elements always stay contiguous by construction), and
        # the small set of distinct ordinals, kept sorted. Lets add() splice
        # directly instead of scanning the whole list to find where a new
        # ordinal belongs. Unused (and left empty) when a comparator is set -
        # that path keeps the original O(graph size) scan, since an arbitrary
        # comparator can't be indexed this way and nothing shows it's hot.
        self._ordinal_tail: dict[int, Element] = {}
        self._sorted_ordinals: list[int] = []

    def __str__(self) -> str:
        return f"Graph({self.id})"

    def __repr__(self) -> str:
        return self.__str__()

    def _weight(self, prev: Element | None, next: Element | None) -> Decimal:
        p_weight = prev.weight if prev else Decimal(0)
        n_weight = next.weight if next else p_weight + Decimal(100)
        return (p_weight + n_weight) / Decimal(2)

    def add(self, obj: Hashable, ordinal: int = 0) -> Element:
        if self.comparator:
            added_element = self._add_scan(obj, ordinal)
        else:
            added_element = self._add_by_ordinal(obj, ordinal)

        if added_element.next is None:
            self.last = added_element

        # adjust cursors
        for name, cursor in self.cursors.items():
            if added_element.next == cursor:
                # If the element being added is just before the cursor, adjust it
                self.cursors[name] = added_element

        return added_element

    def _add_scan(self, obj: Hashable, ordinal: int) -> Element:
        # Comparator-based ordering: an arbitrary total order over obj, not
        # indexable by ordinal the way the default path is. No evidence this
        # path is ever hot in practice - kept as the original O(graph size)
        # linear scan rather than building a general order-statistics
        # structure for an unevidenced cost.
        if not self.first:
            first_element = Element(None, None, obj, ordinal, self._weight(None, None))
            self.first = first_element
            return first_element

        added_element: Element | None = None
        last: Element | None = None
        element: Element | None = self.first
        while element:
            ins = self.comparator(obj, element.obj) < 0 if self.comparator else False
            if ins:
                added_element = self._insert(obj, ordinal, element)
                break
            last = element
            element = element.next

        if not added_element:
            added_element = Element(last, None, obj, ordinal, self._weight(last, None))
            if last is not None:
                last.next = added_element
        return added_element

    def _add_by_ordinal(self, obj: Hashable, ordinal: int) -> Element:
        tail = self._ordinal_tail.get(ordinal)
        if tail is not None:
            added_element = self._insert_after(obj, ordinal, tail)
        else:
            idx = bisect.bisect_left(self._sorted_ordinals, ordinal)
            prev = self._ordinal_tail[self._sorted_ordinals[idx - 1]] if idx > 0 else None
            if prev is not None:
                added_element = self._insert_after(obj, ordinal, prev)
            else:
                next_el = self.first
                added_element = Element(None, next_el, obj, ordinal, self._weight(None, next_el))
                if next_el:
                    next_el.prev = added_element
                self.first = added_element
            self._sorted_ordinals.insert(idx, ordinal)
        self._ordinal_tail[ordinal] = added_element
        return added_element

    def _insert_after(self, obj: Hashable, ordinal: int, prev: Element) -> Element:
        next_el = prev.next
        element = Element(prev, next_el, obj, ordinal, self._weight(prev, next_el))
        prev.next = element
        if next_el:
            next_el.prev = element
        return element

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

        if self.last is element:
            self.last = prev

        if self.comparator is None and self._ordinal_tail.get(element.ordinal) is element:
            # This element was the tail of its ordinal's contiguous run -
            # the index needs to follow the run's new tail, or be dropped
            # entirely if this was the run's only element.
            ordinal = element.ordinal
            if prev is not None and prev.ordinal == ordinal:
                self._ordinal_tail[ordinal] = prev
            else:
                del self._ordinal_tail[ordinal]
                idx = bisect.bisect_left(self._sorted_ordinals, ordinal)
                if idx < len(self._sorted_ordinals) and self._sorted_ordinals[idx] == ordinal:
                    self._sorted_ordinals.pop(idx)

        for name,cursor in self.cursors.items():
            if element == cursor:
                # If this element is currently being iterated on, move the pointer forward
                self.cursors[name] = next

        return next

    def new_cursor(self, cursor_name: str = 'default', element: Element | None = None) -> None:
        if not element:
            self.cursors[cursor_name] = self.first
        else:
            self.cursors[cursor_name] = element

    def get_cursor(self, cursor_name: str = 'default') -> Element | None:
        return self.cursors[cursor_name]

    def next(self, cursor_name: str = 'default') -> Hashable:
        return (cursor := self.next_element(cursor_name)) and cursor.obj

    @trace(level=13, filter=lambda args,kwargs: len(args) < 2 or args[1] == 'default')
    def next_element(self, cursor_name: str = 'default') -> Element | None:
        cursor = self.cursors[cursor_name]
        if not cursor:
            return None
        self.cursors[cursor_name] = cursor.next
        return cursor

    @trace(level=13, filter=lambda args,kwargs: len(args) < 2 or args[1] == 'default')
    def next_elements(self, cursor_name: str = 'default') -> list[Element]:
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

    def cursor_is_left_of(self, element: Element, cursor_name: str = 'default') -> bool:
        cursor = self.cursors[cursor_name]
        return self.compare(cursor, element) < 0 if cursor else False

    def cursor_is_right_of(self, element: Element, cursor_name: str = 'default') -> bool:
        cursor = self.cursors[cursor_name]
        return self.compare(cursor, element) > 0 if cursor else False

    def cursor_is_on(self, element: Element, cursor_name: str = 'default') -> bool:
        cursor = self.cursors[cursor_name]
        return self.compare(cursor, element) == 0 if cursor else False

    def to_list(self, cursor_name: str = 'default', element: Element | None = None) -> list[Hashable]:
        result = []
        self.new_cursor(cursor_name, element)
        while True:
            obj = self.next(cursor_name)
            if obj is None:
                break
            result.append(obj)
        return result

    def to_element_list(self, cursor_name: str = 'default', element: Element | None = None) -> list[Element]:
        result = []
        self.new_cursor(cursor_name, element)
        while element:= self.next_element(cursor_name):
            result.append(element)
        return result
