use pyo3::prelude::*;
use pyo3::types::{PyAny, PySet, PySetMethods};

#[pyfunction]
#[pyo3(signature = (ll, include_only=None))]
pub fn combinations<'py>(
    py: Python<'py>,
    ll: Vec<Bound<'py, PyAny>>,
    include_only: Option<Bound<'py, PyAny>>,
) -> PyResult<Vec<Vec<PyObject>>> {
    // Each position's population can be any iterable (list, set, ...), not
    // just a Sequence - mirrors the pure-Python `for x in ll[i]:` loop, which
    // makes no assumption about the container type either.
    let ll: Vec<Vec<PyObject>> = ll
        .iter()
        .map(|population| {
            population
                .try_iter()?
                .map(|item| item.map(|b| b.unbind()))
                .collect::<PyResult<Vec<PyObject>>>()
        })
        .collect::<PyResult<Vec<Vec<PyObject>>>>()?;

    let use_filter = match &include_only {
        None => false,
        Some(obj) => obj.is_truthy()?,
    };
    if !use_filter {
        return Ok(cartesian(py, &ll));
    }
    let set_type = py.import("builtins")?.getattr("set")?;
    let set_obj = set_type.call1((include_only.unwrap(),))?;
    let set = set_obj.downcast_into::<PySet>()?;

    let mut result = Vec::new();
    let mut prefix: Vec<PyObject> = Vec::with_capacity(ll.len());
    append_matching(py, &ll, 0, &mut prefix, false, &set, &mut result)?;
    Ok(result)
}

fn append_matching(
    py: Python<'_>,
    ll: &[Vec<PyObject>],
    i: usize,
    prefix: &mut Vec<PyObject>,
    satisfied: bool,
    include_only: &Bound<'_, PySet>,
    result: &mut Vec<Vec<PyObject>>,
) -> PyResult<()> {
    if satisfied {
        append_all(py, ll, i, prefix, result);
        return Ok(());
    }
    if i == ll.len() {
        return Ok(());
    }
    for x in &ll[i] {
        prefix.push(x.clone_ref(py));
        let is_member = include_only.contains(x.bind(py))?;
        append_matching(py, ll, i + 1, prefix, is_member, include_only, result)?;
        prefix.pop();
    }
    Ok(())
}

fn append_all(
    py: Python<'_>,
    ll: &[Vec<PyObject>],
    i: usize,
    prefix: &mut Vec<PyObject>,
    result: &mut Vec<Vec<PyObject>>,
) {
    if i == ll.len() {
        result.push(prefix.iter().map(|x| x.clone_ref(py)).collect());
        return;
    }
    for x in &ll[i] {
        prefix.push(x.clone_ref(py));
        append_all(py, ll, i + 1, prefix, result);
        prefix.pop();
    }
}

fn cartesian(py: Python<'_>, ll: &[Vec<PyObject>]) -> Vec<Vec<PyObject>> {
    let mut result: Vec<Vec<PyObject>> = vec![Vec::new()];
    for l in ll {
        let mut new_result = Vec::with_capacity(result.len() * l.len().max(1));
        for prefix in &result {
            for x in l {
                let mut combined: Vec<PyObject> = prefix.iter().map(|p| p.clone_ref(py)).collect();
                combined.push(x.clone_ref(py));
                new_result.push(combined);
            }
        }
        result = new_result;
    }
    result
}
