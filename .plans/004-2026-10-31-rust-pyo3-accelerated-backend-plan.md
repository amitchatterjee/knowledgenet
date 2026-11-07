# Rust/PyO3-accelerated backend for Graph, Factset indexes, and perm.py

Status: **Phase 4 DONE (2026-11-05)** — `Graph`'s ordinal path and `Factset`'s index dicts ported; Phases 5-6 not started. See "Phase 1/2/3/4 results" below.

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
packages); `maturin` was not yet installed — installed as part of Phase 1 (`uv tool install maturin`,
plus added to `dependency-groups.dev`; `maturin==1.16.0`).

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

#### Phase 1 — Scaffolding, no real logic — DONE (2026-11-02)

Installed `maturin` (as a `uv` tool, and added to `dependency-groups.dev`). Stood up `rust/Cargo.toml`
+ `rust/src/lib.rs` (a stub `knowledgenet._native` module exposing one trivial `backend_name()`
function - no ported logic). Switched `pyproject.toml`'s `[build-system]` to `maturin`, added
`[tool.maturin]` (`manifest-path`, `python-source = "src"`, `module-name = "knowledgenet._native"`),
and extended `[tool.uv] cache-keys` with `rust/**/*.rs`/`Cargo.toml` (confirmed: a plain `uv sync`,
no `--reinstall-package` needed, now picks up Rust-only source edits the same way it already did for
Python edits). Added `backend: Literal['auto','native','pure'] = 'auto'` threaded through
`Service.__init__` → `Session.__init__` → stored as `self.backend` (resolved via a new
`core/session.py:_resolve_backend()`, gated behind a top-level `try/except ImportError` on
`from knowledgenet import _native`). Added `src/knowledgenet/_native.pyi` (hand-written stub, per the
plan's mypy note). Added CI Rust-toolchain step (`dtolnay/rust-toolchain@stable`) to `ci.yml`, before
`uv sync --group dev`. Extended `docs/readme-development.md` with the one-time Rust/`rustup` setup
and the `uv run maturin develop --release` fast inner-loop note. Added `test/unit/test_backend_selection.py`
(9 cases: `_resolve_backend`'s three branches including the native-unavailable error path via
monkeypatch, plus end-to-end `Service(...).execute()` under each backend value).

**Two corrections to this plan's assumptions, found while actually building it:**

1. **PyO3 0.24's abi3-py313 feature still rejects a 3.14 interpreter at build time**, even though
   3.14 is ABI-compatible with the stable 3.13 ABI we're targeting - PyO3 caps the *interpreter*
   version it will build against per release, independent of the abi3 target version, and that cap
   lags new CPython releases. Confirmed this is PyO3's own build-time guard, not a real
   incompatibility, by building successfully once `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` is set.
   Rather than requiring every caller (local dev, CI, publish) to remember to set that env var,
   added `rust/.cargo/config.toml` with an `[env]` table - cargo picks this up automatically for any
   invocation rooted at or under `rust/` (confirmed via a standalone `--manifest-path` test from an
   unrelated cwd), so `uv sync`/`maturin develop`/CI all get it for free with no caller-side setup.
2. **"Pure Python is always available" is a *runtime* property, not a build-time one.** Verified by
   stripping Rust/a C linker from `PATH` and running `uv sync --reinstall-package knowledgenet`:
   maturin fails outright ("💥 maturin failed... Error: command ['maturin', 'pep517', ...] returned
   non-zero exit status 1") - there is no silent fallback to a pure-Python install. This matches
   every other PyO3/maturin package's tradeoff (same as `pydantic-core`/`orjson`/`cryptography`): a
   Rust toolchain is required to build `knowledgenet` **from source** (this repo's own `uv sync`,
   and `autoins`'s local path dependency), full stop. The "always available" guarantee holds at two
   other levels instead - `backend='pure'` is always selectable even when the native extension is
   built (for debugging/parity), and once Phase 5/the publish workflow ships a wheel matrix, end
   users on a supported platform install a prebuilt wheel and need no Rust toolchain at all. Updated
   `docs/readme-development.md` to state this plainly rather than imply a graceful degradation that
   doesn't exist.

Verify (all re-run after the corrections above, all green): `uv run mypy src/knowledgenet` clean (21
source files); `uv run pytest -q` - 136 passed (129 prior + 7 new `test_backend_selection.py` cases);
`cd knowledgenet-examples/autoins && uv sync --reinstall-package knowledgenet` rebuilds cleanly
through the maturin-backed path dependency with no change needed on `autoins`'s side, and its 5-test
checksum suite stays green (`uv run pytest -rPX -q`).

#### Phase 2 — Port `core/perm.py` — DONE (2026-11-05)

`rust/src/perm.rs` ports `combinations()` (both the plain-cartesian and `include_only`-filtered
paths; `_append_matching`/`_append_all`/`cartesian()` collapse into one Rust function since there's
no callback boundary to preserve between them). Each when-clause's population is consumed via
Python's iterator protocol rather than required to be a `Sequence`, since `ll[i]` can be a `set`
(e.g. `Collector`/`EventFact` populations) as well as a `list` — this was the one surprise versus
the plan's original signature assumption, caught by the existing test suite (`TypeError: argument
'll': 'set' object cannot be converted to 'Sequence'`) rather than by design review.

`core/perm.py`'s `combinations()` gained a `backend: Literal['native', 'pure'] = 'pure'` parameter
(own top-level `try/except ImportError` block, same shape as `core/session.py`'s) and
`Session._add_facts`'s one call site now passes `backend=self.backend`. `cartesian()` itself stays
pure-Python-only — it's not on the backend-selectable path (callers of `combinations()` are the only
ones whose backend matters), and its own direct tests don't need native parity.

`test/unit/test_perm.py`'s existing `test_combinations_*` tests gained a `backend` parametrization
(`'pure'`/`'native'`, the latter skipped if `knowledgenet._native` isn't built) rather than a
separate parity file — same assertions, same naive-reference comparisons, now run against both
backends.

**Isolated measurement** (`profile_engine.py --mode profile --count 300`, single `execute()` call,
604 input facts / 904 result facts): `core/perm.py`'s `combinations()` cumtime dropped from 0.056s
(pure) to 0.012s (native) — about 4.5x faster for this function alone — but it's <1% of total
`execute()` time either way (engine bucket alone is ~8.2s), so end-to-end wall-clock
(`--mode time --count 300 --repeats 3`) shows no measurable difference (native 3115.6ms avg vs. pure
3146.3ms avg — within run-to-run noise). This is the expected, plan-anticipated result, not a
regression: Phase 5's 2x+ target is about the three ports' *compounded* effect once Graph (Phase 3)
and Factset (Phase 4) land, not any single phase in isolation. `profile_engine.py` gained a
`--backend {auto,native,pure}` flag (threaded through `rule_runner.init_rules`) to make this
comparison repeatable for Phases 3-5 as well.

#### Phase 3 — Port `Graph`'s ordinal fast path — DONE (2026-11-05)

**Scope ceiling found before starting:** profiling `execute()` at 300 claims showed `graph.py` +
`factset.py` combined are only ~5-6% of total time (`node.py`'s rule-callback dispatch and
tracer/logging overhead dominate, both out of scope here). Raised with the user before
implementing - decision: proceed anyway. Rationale given: the infrastructure (native `Element`
type, PyO3 patterns, backend-selection plumbing) is worth building even if this phase's own
speedup is capped, since it's reusable for porting heavier logic later.

**Design, revised from the original plan text during implementation:** rather than keep `Element`
a pure-Python class and have Rust hold only an auxiliary index, `rust/src/graph.rs` defines
`Element` itself as a PyO3 class (same attribute shape: `prev`/`next`/`obj`/`ordinal`/`weight`),
used uniformly by both Graph paths - so the comparator-scan path's own algorithm is genuinely
unchanged Python, just constructing a differently-backed object. `OrdinalIndex` (also native) owns
only `_ordinal_tail`/`_sorted_ordinals`; `Graph.first`/`.last`/`.cursors` stay Python-owned
attributes that `_add_by_ordinal`/`delete_element` update from the native calls' return values -
one place still owns "what the graph looks like." `decimal.Decimal` weights are computed via
callbacks into Python's own `decimal` module from Rust (not reimplemented), since the
order-maintenance scheme's correctness depends on exact (not floating-point) halving.

**A second port was tried and reverted:** `next_element` (plain cursor advancement, comparator-
agnostic) was ported too, since it's callback-free and, per `.plans/004`'s original design table,
listed alongside the others. Measured regression: at this call's volume (~3M times per `execute()`
at 300 claims), the native version's tottime was *2.6x worse* than pure Python's (0.92s vs 0.35s) -
PyO3's FFI-crossing cost exceeds what CPython 3.14's specializing interpreter already does for a
3-line dict-subscript-plus-attribute-load body. `next_element` stays pure Python unconditionally
regardless of backend; no native equivalent exists. This is the clearest evidence in this plan so
far that "callback-free" is necessary but not sufficient for a Rust port to pay off - call
frequency and body triviality matter just as much.

`test/unit/test_graph.py`'s existing tests gained a `backend` parametrization (`'pure'`/`'native'`),
same pattern as Phase 2's `test_perm.py` - all 15 existing cases now run under both.

#### Phase 4 — Port `Factset`'s index dicts — DONE (2026-11-05)

`rust/src/factset.rs` provides two generic helpers - `add_to_dict_of_sets` (the "get-or-create the
set at `key`, add `value`" pattern shared by `_add_to_type_facts_dict`/`_add_to_type_collectors_dict`/
`add_to_group_collectors_dict`/`_add_to_group_events_dict`/`_add_to_type_events_dict`) and
`population` (the `_population()` lookup) - operating directly on the existing Python `dict`/`set`
objects (no Rust-side hash map; same reasoning as Phase 2's `combinations()`: reimplementing
hashing/equality for arbitrary fact objects would mean calling back into Python's `__hash__`/`__eq__`
anyway). `add_facts`/`update_facts`/`del_facts` are unchanged, as scoped - they keep orchestrating
`Collector`/`EventFact` objects in Python, just calling through the native helpers for the index
mutation itself. `test/unit/test_factset.py` gained the same `backend` parametrization, including
`test_population_returns_the_live_index_set` - its identity assertion (`_population(...) is
_type_to_facts[...]`) holds under native too, since `population()` returns the same stored `PySet`
object rather than a copy.

**Isolated measurement** (`profile_engine.py --mode profile --count 300`): `graph.py`+`factset.py`
combined tottime dropped from 0.633s (pure) to 0.583s (native) - about 8% off that bucket, consistent
with Phase 3's insertion-path-only win (`_add_by_ordinal`+`add`: 0.146s native vs 0.186s pure, ~21%
faster) since `next_element` (the bucket's single largest line item, ~0.34s either way) stays
identical pure Python under both backends now. End-to-end wall-clock (`--mode time --count 300
--repeats 5`) shows native modestly ahead of pure (3182ms vs 3374ms avg, ~6%) - small, but real and
no longer masked by the `next_element` regression that an earlier (reverted) version of this phase
introduced. Still nowhere near 2x alone, as expected from the scope-ceiling finding above - Phase 5
is where the compounded picture against all four phases gets measured.

#### Post-Phase-4 addendum — `KNOWLEDGENET_BACKEND` env var, default flipped to `pure` (2026-11-07)

Two changes made after Phase 4 landed, before starting Phase 5:

1. **`KNOWLEDGENET_BACKEND` env var.** `_resolve_backend()` (duplicated in `core/session.py`,
   `core/graph.py`, `factset.py` — see "Backend selection" above for why) now checks this env var
   when the caller passes `'auto'`. An explicit `'native'`/`'pure'` argument always wins over the
   environment — it's the caller's deliberate choice, e.g. a parity test pinning a backend, not
   something a deployment-level setting should override. An unrecognized env var value raises
   `ValueError` rather than being silently ignored. This reverses the "no env var" call made in the
   original "Backend selection" design above — the ops need flagged there as the condition for
   adding one actually surfaced (see point 2).

2. **Default flipped from `'auto'` to `'pure'`** across `Service`, `Session`, `Graph`, `Factset`
   (and `autoins`'s `rule_runner.py::init_rules`). Reasoning: the intended consumer raised that the
   rules engine runs inside PySpark executors — separate processes on worker nodes whose OS/glibc/
   Python ABI must match a prebuilt wheel, or else need a Rust toolchain baked into the executor
   image/init script. Neither is true yet (the CI wheel-matrix/publish step is designed, not
   shipped), so defaulting to `'auto'` meant silently attempting native wherever the extension
   happened to be importable, including on an executor where it only builds by accident. `'pure'` as
   the hard default removes that surprise; `'auto'`/`'native'` remain fully available, just no longer
   the default path. Combined with point 1: since `'pure'` is now a literal default rather than
   `'auto'`, the env var only takes effect for a caller that explicitly opts into `backend='auto'` —
   it does not make native fire by itself when nothing passes `'auto'`.

Verification: `uv run mypy src/knowledgenet` clean; `uv run pytest -q` (172 passed, +7 new tests in
`test/unit/test_backend_selection.py` covering the env var across all three independent
`_resolve_backend` copies); `autoins`'s `uv sync --reinstall-package knowledgenet` + checksum suite
(5 passed) confirming the default flip changes no observable output.

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
