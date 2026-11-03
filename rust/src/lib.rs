//! Stub native backend (.plans/004 Phase 1). No ported logic yet - this
//! module exists only to prove the build/import/fallback-detection path
//! works end to end before anything real moves into it.

use pyo3::prelude::*;

#[pyfunction]
fn backend_name() -> &'static str {
    "native"
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(backend_name, m)?)?;
    Ok(())
}
