use std::collections::HashMap;

use pyo3::prelude::*;

/// Same shape as the pure-Python `core/graph.py::Element` it replaces when
/// `backend='native'` - a plain doubly-linked-list node. Used uniformly by
/// both Graph paths (ordinal and comparator-scan): the comparator path's own
/// algorithm is unchanged Python, it just builds these instead of the pure
/// class.
#[pyclass]
pub struct Element {
    #[pyo3(get, set)]
    pub prev: Option<Py<Element>>,
    #[pyo3(get, set)]
    pub next: Option<Py<Element>>,
    #[pyo3(get, set)]
    pub obj: PyObject,
    #[pyo3(get, set)]
    pub ordinal: i64,
    #[pyo3(get, set)]
    pub weight: PyObject,
}

#[pymethods]
impl Element {
    #[new]
    fn new(
        prev: Option<Py<Element>>,
        next: Option<Py<Element>>,
        obj: PyObject,
        ordinal: i64,
        weight: PyObject,
    ) -> Self {
        Element { prev, next, obj, ordinal, weight }
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let obj_str = self.obj.bind(py).str()?;
        let weight_str = self.weight.bind(py).str()?;
        Ok(format!("Element:({}, weight:{})", obj_str, weight_str))
    }

    fn __str__(&self, py: Python<'_>) -> PyResult<String> {
        self.__repr__(py)
    }
}

fn decimal_weight(
    py: Python<'_>,
    prev: Option<&Py<Element>>,
    next: Option<&Py<Element>>,
) -> PyResult<PyObject> {
    let decimal_cls = py.import("decimal")?.getattr("Decimal")?;
    let p_weight = match prev {
        Some(p) => p.borrow(py).weight.clone_ref(py).into_bound(py),
        None => decimal_cls.call1((0,))?,
    };
    let n_weight = match next {
        Some(n) => n.borrow(py).weight.clone_ref(py).into_bound(py),
        None => {
            let hundred = decimal_cls.call1((100,))?;
            p_weight.call_method1("__add__", (hundred,))?
        }
    };
    let total = p_weight.call_method1("__add__", (n_weight,))?;
    let two = decimal_cls.call1((2,))?;
    let result = total.call_method1("__truediv__", (two,))?;
    Ok(result.unbind())
}

fn insert_after(
    py: Python<'_>,
    obj: PyObject,
    ordinal: i64,
    prev: &Py<Element>,
) -> PyResult<Py<Element>> {
    let next_el = prev.borrow(py).next.as_ref().map(|e| e.clone_ref(py));
    let weight = decimal_weight(py, Some(prev), next_el.as_ref())?;
    let element = Py::new(
        py,
        Element {
            prev: Some(prev.clone_ref(py)),
            next: next_el.as_ref().map(|e| e.clone_ref(py)),
            obj,
            ordinal,
            weight,
        },
    )?;
    prev.borrow_mut(py).next = Some(element.clone_ref(py));
    if let Some(n) = next_el {
        n.borrow_mut(py).prev = Some(element.clone_ref(py));
    }
    Ok(element)
}

/// Native-backed replacement for `core/graph.py`'s `_ordinal_tail`/
/// `_sorted_ordinals` dict+list pair, used only when `comparator is None`
/// (the ordinal fast path). Owns no other Graph state - `first`/`last`/
/// `cursors` stay Python attributes, updated by the caller from this
/// object's return values, so there is exactly one place (`core/graph.py`)
/// that owns "what does the graph currently look like".
#[pyclass]
pub struct OrdinalIndex {
    ordinal_tail: HashMap<i64, Py<Element>>,
    sorted_ordinals: Vec<i64>,
}

#[pymethods]
impl OrdinalIndex {
    #[new]
    fn new() -> Self {
        OrdinalIndex { ordinal_tail: HashMap::new(), sorted_ordinals: Vec::new() }
    }

    /// Mirrors `_add_by_ordinal`. Returns (new_element, updated_first) -
    /// `updated_first` is always given back (unchanged if the insert didn't
    /// touch the head) so the caller can unconditionally assign it to
    /// `self.first`.
    fn add(
        &mut self,
        py: Python<'_>,
        first: Option<Py<Element>>,
        obj: PyObject,
        ordinal: i64,
    ) -> PyResult<(Py<Element>, Option<Py<Element>>)> {
        let existing_tail = self.ordinal_tail.get(&ordinal).map(|e| e.clone_ref(py));
        let (added, new_first) = if let Some(tail_elem) = existing_tail {
            let added = insert_after(py, obj, ordinal, &tail_elem)?;
            (added, first)
        } else {
            let idx = self.sorted_ordinals.partition_point(|&o| o < ordinal);
            let prev = if idx > 0 {
                self.ordinal_tail.get(&self.sorted_ordinals[idx - 1]).map(|e| e.clone_ref(py))
            } else {
                None
            };
            let (added, new_first) = if let Some(prev_elem) = prev {
                let added = insert_after(py, obj, ordinal, &prev_elem)?;
                (added, first)
            } else {
                let next_el = first;
                let weight = decimal_weight(py, None, next_el.as_ref())?;
                let added = Py::new(
                    py,
                    Element {
                        prev: None,
                        next: next_el.as_ref().map(|e| e.clone_ref(py)),
                        obj,
                        ordinal,
                        weight,
                    },
                )?;
                if let Some(n) = &next_el {
                    n.borrow_mut(py).prev = Some(added.clone_ref(py));
                }
                (added.clone_ref(py), Some(added))
            };
            self.sorted_ordinals.insert(idx, ordinal);
            (added, new_first)
        };
        self.ordinal_tail.insert(ordinal, added.clone_ref(py));
        Ok((added, new_first))
    }

    /// Mirrors the ordinal-index-specific block of `delete_element` - the
    /// pointer splice itself, `last` tracking, and cursor adjustment are
    /// shared with the comparator path and stay in Python.
    fn on_delete(
        &mut self,
        py: Python<'_>,
        element: Py<Element>,
        prev: Option<Py<Element>>,
    ) -> PyResult<()> {
        let ordinal = element.borrow(py).ordinal;
        let is_tail = match self.ordinal_tail.get(&ordinal) {
            Some(tail) => tail.as_ptr() == element.as_ptr(),
            None => false,
        };
        if !is_tail {
            return Ok(());
        }
        let prev_matches_ordinal = match &prev {
            Some(p) => p.borrow(py).ordinal == ordinal,
            None => false,
        };
        if prev_matches_ordinal {
            self.ordinal_tail.insert(ordinal, prev.unwrap());
        } else {
            self.ordinal_tail.remove(&ordinal);
            let idx = self.sorted_ordinals.partition_point(|&o| o < ordinal);
            if idx < self.sorted_ordinals.len() && self.sorted_ordinals[idx] == ordinal {
                self.sorted_ordinals.remove(idx);
            }
        }
        Ok(())
    }
}

// Deliberately no native `next_element` here: at the ~3M calls/execute()
// this sees, PyO3's FFI-crossing cost exceeds CPython's already
// inline-cached dict-subscript/attribute-load for this trivial body - see
// core/graph.py::Graph.next_element.
