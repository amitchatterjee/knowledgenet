# Rust/PyO3-accelerated backend for Graph, Factset indexes, and perm.py

Status: **NOT STARTED (2026-10-31)** — plan only, no code/build/CI changes made yet.

## Context

Plan `002-2026-10-10-precompilation-options-exploratory-plan.md` measured a narrow PyO3
microbenchmark (just `Graph`'s ordinal index) at 1.3-1.7x and explicitly flagged "a real, scoped
Rust port of specific engine-internal hot spots (`Graph`, `Factset`'s indexes, `Collector`)" as
**separate, larger-scope work, out of that plan's bounds**. This plan is that follow-on: a real
port of the three *callback-free* bookkeeping hot spots identified during this session's
exploration — `core/graph.py`'s ordinal fast path, `factset.py`'s index dicts, and `core/perm.py`'s
`combinations()` — compiled via Rust+PyO3, with the existing pure-Python implementations kept
in place as a permanent, always-available fallback and an explicit alternative (not a transitional
scaffold to delete later).

The user's goal is a compounded 2x+ end-to-end speedup (not just per-function), achieved by porting
three internals that interact on every `Session._add_facts` call, rather than one isolated function
as the 002 spike did. Two packaging/scope decisions were made explicitly with the user before this
plan was written:

- **Single PyPI package, auto-detecting backend** (not two separate packages). `knowledgenet` ships
  platform-specific wheels bundling both implementations; native is used automatically when
  importable, pure Python is the fallback and an explicit override. Standard PyO3/maturin idiom
  (same shape as `pydantic-core`, `orjson`, `cryptography`).
- **`Collector` (`container.py`) is explicitly out of scope.** Its hot methods (`_filter_obj`,
  `sum`/`variance`/`minimum`/`maximum`) call rule-author-supplied callables as part of their
  contract, so a Rust port there would mostly wrap a Python callback crossing rather than eliminate
  one — capped payoff, real risk, and it's genuinely public API (`autoins/fact_io.py` constructs
  `Collector` directly). Revisit only if later profiling shows it's still hot after the three in
  scope land.

Toolchain check at plan-writing time: `cargo`/`rustc` 1.99.1 already present on this machine (system
packages); `maturin` is **not yet installed** — needed before Phase 1 starts.

## What's being ported, and what stays pure Python always

Research (reading `core/graph.py`, `factset.py`, `core/perm.py`, `container.py`, and every call site
in `core/session.py`/`node.py`) established exactly which code is callback-free bookkeeping (safe to
port) versus code that calls back into rule-author closures (must stay Python, even in "native
mode"):

| Module | Port (callback-free) | Stays Python always |
|---|---|---|
| `core/graph.py` | `_add_by_ordinal`, `_insert_after`, `delete_element`, `next_element`, the `_ordinal_tail`/`_sorted_ordinals` index | `_add_scan`/`_insert` (the `comparator`-based path — `comparator` is an arbitrary callable, e.g. `node_sorter`) |
| `factset.py` | The 5 index dicts' pure get/set/membership ops (`_add_to_type_facts_dict` etc.), `_population()` | `add_facts`/`update_facts`/`del_facts`'s *orchestration* — these call `collector.add/remove/reset_cache()` and must keep invoking Python `Collector`/`EventFact` objects |
| `core/perm.py` | `combinations()`, `_append_matching`, `_append_all`, `cartesian()` — 100% pure, zero callbacks anywhere | n/a — the whole module qualifies |

This means `Graph` becomes a **hybrid class**: ordinal-path operations delegate to the Rust
structure, comparator-path operations stay on the existing Python code unchanged. `Factset` stays a
Python class too — only its backing index dicts swap to a Rust-backed structure; the
Collector/EventFact notification loops in `add_facts`/`update_facts`/`del_facts` are untouched
Python calling into those same Python `Collector`/`EventFact` objects as today.

The only existing seam for a pure-Python/native switch is `Session.execute()`
(`core/session.py:44-45`, where `Factset()`/`Graph(...)` are constructed fresh per session) — there
is no factory/DI layer anywhere in the codebase today.

## Design

### Backend selection

Add a `backend: Literal['auto', 'native', 'pure'] = 'auto'` parameter threaded through
`Service.__init__` → `Session.__init__` → `Session.execute()`, mirroring exactly how `node_sorter`
is already threaded through that same path (`service.py:34`, `session.py` ctor). `'auto'` (default):
use the native implementation if `knowledgenet._native` is importable, else pure Python, decided
once at import time via a top-level `try/except ImportError` in `core/session.py` (and `factset.py`
for its index swap), not re-checked per call. `'native'`/`'pure'` force a choice explicitly (useful
for debugging/parity testing and for ops who want to guarantee one behavior regardless of what's
installed). No env var in this plan — a constructor parameter is simpler to test and avoids global
mutable state; add one later only if an ops need actually surfaces.

### Rust crate layout

New `rust/` directory at the `knowledgenet` repo root (sibling to `src/`), a single PyO3 crate
(`Cargo.toml` + `rust/src/lib.rs` + one module per ported component: `graph.rs`, `factset_index.rs`,
`perm.rs`), built via **maturin** in mixed Rust/Python project mode — Python sources stay exactly
where they are (`src/knowledgenet/`), maturin just also compiles the Rust crate into a
`knowledgenet._native` extension module and bundles both into one wheel. Use PyO3's `abi3-py313`
feature so one wheel per OS/arch covers every supported Python version (3.13+) — keeps the CI wheel
matrix to platform×arch, not platform×arch×python-version.

### Build system changes

- `[build-system]` in `pyproject.toml`: `setuptools` → `maturin` (`requires = ["maturin>=1.7,<2.0"]`,
  `build-backend = "maturin"`), plus a `[tool.maturin]` section pointing at `rust/Cargo.toml` and the
  existing `src/knowledgenet` Python source layout.
- `uv sync`/`uv sync --reinstall-package knowledgenet` must still "just work" for `autoins`'s local
  path dependency (`knowledgenet-examples/autoins/pyproject.toml`'s `[tool.uv.sources]`) — uv
  supports building maturin-backend path dependencies natively, so this should need no change on
  `autoins`'s side, only `knowledgenet`'s own `[tool.uv] cache-keys` (currently watches
  `src/**/*.py`) extended to also watch `rust/**/*.rs` and `Cargo.toml`, so a Rust-only change is
  detected by plain `uv sync` the same way a Python-only change already is today.
- `.github/workflows/ci.yml`: add a Rust toolchain step (`dtolnay/rust-toolchain` or equivalent)
  before `uv sync --group dev`, since running tests now requires building the extension once.
- `.github/workflows/python-publish.yml`: replace the current single `python -m build` step with a
  `maturin-action`-driven matrix (manylinux x86_64 + aarch64, macOS x86_64 + arm64, Windows x86_64),
  each producing a wheel, uploaded as artifacts and published together via the existing
  `pypa/gh-action-pypi-publish` OIDC step (unchanged) plus one sdist build (source fallback — still
  requires a Rust toolchain to install from on an unlisted platform, same tradeoff every PyO3 PyPI
  package already accepts).
- `docs/readme-development.md`: new one-time-setup step (install `rustup`; confirm `cargo`/`rustc` on
  `PATH`), and the local dev loop gains `uv run maturin develop --release` as the native-extension
  build command (replacing a plain `uv sync` when iterating on the Rust side specifically — this
  belongs in the same section explaining `uv sync --reinstall-package knowledgenet` from plan 003).
- mypy: `core/session.py`'s backend-selection code and any Python-side type annotations referencing
  the native module need a hand-written `src/knowledgenet/_native.pyi` stub (PyO3 doesn't generate
  one automatically; `pyo3-stub-gen` is an option if hand-maintenance becomes a burden) so
  `uv run mypy src/knowledgenet` (CLAUDE.md's `disallow_untyped_defs`, package-wide) stays clean.

### Phasing (mirrors plan 002/003's own "measure before and after every step" discipline)

#### Phase 1 — Scaffolding, no real logic — NOT STARTED

Install `maturin`; stand up the `rust/` crate, maturin build, CI Rust-toolchain step, and the
`auto`/`native`/`pure` selection plumbing with a stub native module (e.g. a trivial always-returns-
pure fallback). Prove install/build/CI/fallback-detection work end-to-end before porting anything.
Verify: `uv run mypy src/knowledgenet` clean, `uv run pytest -q` unchanged pass count, `autoins`'s
`uv sync --reinstall-package knowledgenet` + its own test suite still green.

#### Phase 2 — Port `core/perm.py` — NOT STARTED

Cleanest target — zero callbacks, no persistent state, single call site (`session.py:297`). Add
`test/unit/test_perm.py` parametrization (or a new `test_perm_native_parity.py`) asserting native
and pure-Python `combinations()` produce identical output on the existing test cases. Measure in
isolation via `profile_engine.py`.

#### Phase 3 — Port `Graph`'s ordinal fast path — NOT STARTED

Hybrid class: ordinal operations delegate to Rust, the `comparator`-supplied path stays Python
untouched. Extend `test/unit/test_graph.py` with a native/pure parity check for every existing
ordinal-path test case. Measure in isolation.

#### Phase 4 — Port `Factset`'s index dicts — NOT STARTED

`_population()` and the internal `_add_to_*_dict` mutations move to a Rust-backed structure;
`add_facts`/`update_facts`/`del_facts` keep their existing Python-level Collector/EventFact
orchestration, just reading/writing through the new index. Extend `test/unit/test_factset.py`
(including the existing aliasing test, `test_population_returns_the_live_index_set`, which must
keep passing against whichever backend is active) with a native/pure parity check. Measure in
isolation.

#### Phase 5 — End-to-end measurement — NOT STARTED

Run `test/perf/profile_engine.py` at the same scales used in 002/003 (100-500 claims) with
`backend='native'` vs `backend='pure'`, confirm `autoins`'s checksum-based test suite passes
identically under both, and document the real compounded speedup against the 2x+ target —
including whether it's reached, and if not, by how much and why (e.g., residual Python↔Rust
crossing frequency between the three ported pieces inside one `_add_facts` call).

#### Phase 6 — Possible follow-on (not committed) — NOT STARTED

If Phase 5 falls short of 2x and the gap is crossing-frequency-bound (not per-operation cost), the
next lever would be batching the combinations→graph-insertion sequence into fewer, larger Rust
calls per `_add_facts` invocation instead of one crossing per element — a deeper redesign, not a
continuation of this plan's per-module port shape.

## Verification

- `uv run mypy src/knowledgenet` clean at every phase.
- `uv run pytest -q` — all existing tests pass under the default (`auto`) backend, plus new
  native/pure parity tests pass under both `backend='native'` and `backend='pure'` explicitly.
- `cd knowledgenet-examples/autoins && uv sync --reinstall-package knowledgenet && uv run pytest -rPX -q`
  — checksum-matched expected outputs, confirming zero observable behavior change.
- `test/perf/profile_engine.py --mode time --count 300/500 --repeats 3` run under both backends,
  recorded in a new section of this plan alongside the 2x+ target comparison — same harness used
  throughout 002/003, so numbers stay comparable to prior phases.
