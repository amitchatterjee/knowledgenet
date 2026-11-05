use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PySet};

/// Generic "get-or-create the set at `key`, add `value`" helper - replaces
/// `factset.py`'s `_add_to_type_facts_dict`/`_add_to_type_collectors_dict`/
/// `add_to_group_collectors_dict`/`_add_to_group_events_dict`'s identical
/// bodies (and, called once per type, `_add_to_type_events_dict`'s loop
/// body). One native call instead of the Python `dict.get`-then-`dict[key]
/// =`-two-step for each.
#[pyfunction]
pub fn add_to_dict_of_sets<'py>(
    py: Python<'py>,
    d: &Bound<'py, PyDict>,
    key: Bound<'py, PyAny>,
    value: Bound<'py, PyAny>,
) -> PyResult<()> {
    match d.get_item(&key)? {
        Some(existing) => {
            let set = existing.downcast::<PySet>()?;
            set.add(value)?;
        }
        None => {
            let set = PySet::empty(py)?;
            set.add(value)?;
            d.set_item(key, set)?;
        }
    }
    Ok(())
}

/// Replaces `_population`'s per-dict "return dict[key] if key in dict else
/// set()" lookup.
#[pyfunction]
pub fn population<'py>(
    py: Python<'py>,
    d: &Bound<'py, PyDict>,
    key: Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PySet>> {
    match d.get_item(&key)? {
        Some(existing) => Ok(existing.downcast_into::<PySet>()?),
        None => PySet::empty(py),
    }
}
