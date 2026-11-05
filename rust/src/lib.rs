use pyo3::prelude::*;

mod factset;
mod graph;
mod perm;

#[pyfunction]
fn backend_name() -> &'static str {
    "native"
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(backend_name, m)?)?;
    m.add_function(wrap_pyfunction!(perm::combinations, m)?)?;
    m.add_class::<graph::Element>()?;
    m.add_class::<graph::OrdinalIndex>()?;
    m.add_function(wrap_pyfunction!(factset::add_to_dict_of_sets, m)?)?;
    m.add_function(wrap_pyfunction!(factset::population, m)?)?;
    Ok(())
}
