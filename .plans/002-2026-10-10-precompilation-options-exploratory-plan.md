# Explore precompilation options for faster rule evaluation

Status: **DONE (2026-10-30)** — all phases complete (Phase 0: 2026-10-17; Phases 1-6: 2026-10-26
and 2026-10-30). This was a research/spike plan: each phase was meant to produce a measurement and
a go/no-go judgement, not shipped code - that's exactly how it landed. Phase 0 ran as intended, but
what it found was urgent and actionable enough that it turned into real shipped fixes instead of
just a data point — see `003-2026-10-17-rete-engine-performance-fixes.md`, which is where that work
actually lives (currently paused, not abandoned). Phase 1 (PyPy) was disqualified on resumption
without running a benchmark; Phase 2 (mypyc) was disqualified after a real compile attempt surfaced
a structural incompatibility; Phase 3 (Nuitka) compiled and ran correctly but measured **36%/34%
slower than plain CPython** at 300/500 claims, two-for-two; Phase 4 (Codon) was disqualified even
more fundamentally than expected; Phase 5 (Rust/PyO3, one isolated hot bookkeeping operation)
measured a real but modest **1.3-1.7x** speedup, capped by per-call PyO3 crossing overhead and by
CPython's own list operations already being C. Cython (candidate 3) was never run - it shares
mypyc's Phase 2 disqualification. **Bottom line (Phase 6): no precompilation option clears the bar
as a drop-in adoption today** - see Phase 6's table and recommendation below for the full
comparison and the two live paths forward (plan 003's own unfinished Phase 5, or a real scoped Rust
port of specific engine internals - both out of this plan's scope). One incidental finding from
Phase 2 (a scanner.py reflection fix, widening rule discovery to `callable()` instead of
`inspect.isfunction()`) was kept as a permanent, independently-useful fix regardless of mypyc's
fate.

**Phase 0's finding revises this plan's own premise.** The Context section below assumed rule
bodies dominate runtime (per prior discussion, before any profiling existed) - that's why
precompiling rule bodies looked like the lever worth exploring. Actual profiling (first at a tiny
50-claim smoke scale, then properly at 100-500 claims) found the opposite: `autoins`'s own code
(rule bodies *and* its platform code combined) is under 1% of total runtime; `knowledgenet`'s own
engine bookkeeping is ~77%+, even after four rounds of engine-side fixes (003). Before resuming
Phases 1-6 here, re-examine whether PyPy/mypyc/Nuitka/Codon/Rust are still the right next move at
all — 003's own Phase 5 (an unfixed `O(n^2)`-ish `Factset.find()` re-scan) is a concrete, scoped,
high-confidence engine-side fix that's plausibly higher-leverage than any of them, precisely
because rule bodies were never where the time was going.

## Context

Motivation, from prior discussion (not yet validated with real profiling data — Phase 0 exists to
get that data): knowledgenet's RETE engine internals (graph/node bookkeeping, `FactSet` indexing,
session management) likely cost less than the time spent *inside* rule-author `when`/`then`
expressions themselves, for typical rulesets like `knowledgenet-examples/autoins`. If true, making
the engine's own internals faster (e.g. a Rust rewrite of `core/graph.py`, `factset.py`, etc.) has a
capped payoff — the real hot path is the `matches=lambda ctx, this: ...` / `then=lambda ctx: ...`
closures rule authors write, which is exactly the part of the system the engine treats as opaque
and un-typed by design (see `001-...-DONE.md`'s Design section: `ctx`/`this` are deliberately
dynamic, not an oversight).

**Hard constraint, decided in conversation:** whatever comes out of this exploration must not
require rule authors to write typed or otherwise-constrained code. Rules stay free-form, functional
Python — duck-typed `this`, `assign()`-populated `ctx`, arbitrary closures, `and`-chained
expressions. This constraint is what makes the problem interesting: most "compile Python to native
code" tooling (mypyc, Cython, Codon) gets its speedup specifically *from* static types, so this
plan has to empirically check what, if anything, still works without them — rather than assume any
one tool is the answer.

## Candidates to evaluate, and why each is or isn't disqualified up front

1. **PyPy** (tracing JIT, drop-in CPython replacement) — no type annotations needed, specializes
   hot dynamic code (attribute lookups, repeated closure calls) at runtime. Primary candidate given
   the no-typing constraint. Risk: `opentelemetry-sdk`/`opentelemetry-exporter-otlp` (a runtime dep
   of `knowledgenet`, see `pyproject.toml`) may have C-extension or `grpcio` dependencies with weak
   PyPy support — needs checking, not assumed.
2. **mypyc** — needs static types to pay off; disqualified for rule bodies by the hard constraint
   above, but worth measuring anyway as a **ceiling**: compile the engine (already fully typed per
   `001-...-DONE.md`) and see how much of the total runtime that portion alone represents, to know
   what's being left on the table by not touching rule bodies.
3. **Cython** — same disqualification/rationale as mypyc; not run as its own spike unless Phase 2's
   mypyc numbers suggest it's worth a second data point (Cython's optimizer differs from mypyc's).
   **Not run (2026-10-26):** Phase 2 disqualified mypyc on a structural issue (native classes can't
   hold the dynamic, post-`__init__` attributes `Rule`/`Fact`/`Collector`/etc. rely on by design) -
   Cython's own native-class extension types have the same `__dict__`-less-by-default tension, so
   there's nothing here to learn that Phase 2 didn't already establish.
4. **Nuitka** (whole-program AOT compiler, preserves full Python semantics) — no type annotations
   required, so survives the constraint, but gains on genuinely dynamic duck-typed code are
   typically modest (not Rust/mypyc-level) since it still has to emulate CPython's object model
   faithfully. Worth measuring rather than assuming.
5. **Codon** — AOT compiler to native code, but only for a restricted, more static subset of Python
   (no arbitrary duck typing / monkeypatching / `**kwargs`-driven `setattr`, all of which
   `knowledgenet`'s API uses — see `001-...-DONE.md`'s Design section). Very likely disqualified by
   inspection; Phase 4 is a short feasibility check, not a full port attempt, specifically to confirm
   this before ruling it out for good.
6. **Rust + PyO3 hybrid** (engine internals native, rule bodies stay Python via embedded CPython) —
   already discussed as a separate, larger effort. Included here only as a narrow micro-benchmark
   (Phase 5) to get a real number for "how much does the engine-internals share actually cost,"
   since that number is also what Phase 0's profiling is trying to establish from the other
   direction (measurement, not a rewrite, is in scope here).

## Design — methodology and decision criteria

Every phase runs against the same representative workload: `knowledgenet-examples/autoins`'s
existing `rules/` (5 rulesets, `02_validation` through `05_finalization`) and sample data under
`autoins/data/`, driven via `rule_runner.py`, so numbers are comparable across phases. No synthetic
microbenchmarks except where noted (Phase 5).

Decision criteria recorded for each candidate in Phase 6's writeup:
- **End-to-end speedup** on the autoins run (wall clock, `uv run python src/rule_runner.py ...`
  timed, averaged over a few runs).
- **Constraint on rule-author syntax** — none / some / disqualifying, per the hard constraint above.
- **Compatibility risk** — does it run the existing dependency set (`opentelemetry-*`) unmodified?
- **Packaging/deployment delta** — same `uv`-managed Python CLI, or a new build/runtime artifact?
- **Reversibility** — can it be adopted incrementally (e.g. PyPy is a Python-version swap; Nuitka is
  a build step) or does it require a fork/parallel codebase?

### Phase 0 — Profiling baseline (no tooling changes) — **DONE (2026-10-17)**

Ran via `autoins/test/perf/{generate_data.py,profile_engine.py}` (built as part of this phase) —
synthetic volume datasets at 50-500 claims, `cProfile`'d `Service.execute()` directly, bucketed by
source repo.

**Result: the "rule bodies dominate" premise was wrong.** `knowledgenet` (engine) is ~77%+ of
runtime; `autoins` (rule bodies *and* its own platform code combined) is under 1%; the remainder is
mostly stdlib overhead the engine itself triggers (`logging.debug`, `ContextVar.get`). Measured at
multiple scales (100/150/200/300/500 claims, see `003-2026-10-17-rete-engine-performance-fixes.md`
for the full numbers) — not a one-off reading.

This number is why Phases 1-6 below are paused rather than continued: they were designed to attack
rule-body cost specifically, and rule bodies turned out not to be where the time goes. Also
surfaced, as a side effect of profiling at realistic scale: `Service.execute()` scaled roughly
cubically with claim count and 500 claims didn't complete at all — a concrete algorithmic problem,
not a tooling question, which is what actually got acted on (see 003).

### Phase 1 — PyPy spike — **DISQUALIFIED (2026-10-26), not run**

**Found:** On resuming this plan, checked PyPy availability against the project's `requires-python
= ">=3.13"` floor (`pyproject.toml:19`) before installing anything. Fedora's dnf repo only offers
`pypy3.11` (Python 3.11 semantics) — already short of the 3.13 floor. Checked upstream directly
rather than assume dnf was just behind: [pypy.org/download](https://pypy.org/download.html) and the
[build directory](https://downloads.python.org/pypy/) confirm the latest PyPy release (v8.0.1, and
every version before it) tops out at **Python 3.12** — there is no PyPy build targeting 3.13 from
any source, not a packaging gap specific to Fedora.

**Decision:** Disqualified without running a benchmark. Dropping to 3.11 (dnf) or even 3.12
(upstream) to run this spike would mean either relaxing `requires-python` for the spike (and then
the result wouldn't actually describe the 3.13 runtime the project ships) or testing a version the
project has already moved past — neither produces a number worth acting on. User decision
(2026-10-26): don't go back to 3.11; skip PyPy and proceed directly to Phase 2 (mypyc). If PyPy
ever ships a 3.13+ build, this phase can be reopened using the method below, otherwise unchanged:

~~Install `pypy3` (matching the project's 3.13+ floor), create a PyPy-backed venv for `autoins` +
local-source `knowledgenet` (same `[tool.uv.sources]` path-dependency setup as the CPython venv,
or a plain `pypy3 -m venv` if `uv` + PyPy interact badly — check first), run the same autoins
workload, compare wall-clock against Phase 0's baseline. Check `opentelemetry-sdk`/
`opentelemetry-exporter-otlp` import and basic span export work under PyPy before trusting the
timing (if they don't, note whether tracing can be disabled for the benchmark without invalidating
the comparison). No source changes to `knowledgenet` or `autoins` — the entire point is "does this
work and get faster with zero code changes."~~

### Phase 2 — mypyc ceiling measurement — **DISQUALIFIED (2026-10-26), no benchmark number**

**Found (1 of 2), fixed and kept regardless of mypyc's fate:** Compiled `src/knowledgenet` with
`mypyc` (via `uv run --with setuptools -- mypyc knowledgenet`, from a scratch copy of the package —
clean compile, zero errors, all 19 modules). Running it against `autoins` failed at
`scanner.lookup()` with every rule silently unregistered. Root cause: `scanner.py`'s
`_load_rules_from_module()` gated rule discovery on `inspect.isfunction(obj)`. mypyc compiles
`decorator.py`'s `ruledef()` closure into a native callable object (type
`knowledgenet.decorator.wrapper_ruledef_ruledef_wrapper_obj`), not a `types.FunctionType` —
`__ruledef__` was still set correctly, but `isfunction()` returned `False` for it, so the scanner's
own filter silently skipped every decorated rule before ever checking the marker.

**Fix:** Changed the outer filter in `scanner.py:_load_rules_from_module` from
`inspect.isfunction(obj)` to `callable(obj)`, keeping the existing `getattr(obj, '__ruledef__',
False)` inner check unchanged. Verified this is a strict widening, not a behavior change: under
plain CPython a `@ruledef`-decorated function is already both `isfunction()==True` and
`callable()==True`, so every rule registered today still registers identically; the only change is
that non-`FunctionType` callables (mypyc's native closures) now also reach the `__ruledef__` gate,
which only the `ruledef` decorator itself ever sets, so there's no new false-positive risk. Grepped
for other `inspect.isfunction`/`isclass` usage - only one other site (`core/tracer.py:78`), unrelated
to rule discovery, and it already falls back to a bare `callable()` OR-condition regardless. Added
`test/unit/test_scanning.py::test_rule_loading_non_function_callable`, which simulates the
mypyc-closure shape (callable, not `types.FunctionType`, `__ruledef__` set) without needing an
actual mypyc build, so this stays covered in ordinary CPython CI. `uv run mypy src/knowledgenet` →
clean; `uv run pytest -q` → 124/124 (123 + the new test). **Kept in the codebase independent of
mypyc's outcome below** - it's a real, low-risk robustness fix on its own merits, not spike-only.

**Found (2 of 2), disqualifying - not fixed:** After the scanner fix, rule *discovery* works but
rule *construction* doesn't: `ruledef`'s wrapper does `rule.ruleset = ...` / `rule.repository = ...`
*after* `Rule(...)` is constructed (relying on every Python object having a `__dict__` by default).
mypyc compiles classes into a fixed, struct-like native layout inferred from what `__init__` assigns
by literal name - there's no `__dict__` fallback, so this fails with `AttributeError: 'Rule' object
has no attribute 'ruleset' and no __dict__ for setting new attributes`. This isn't Rule-specific:
grepped for the `**kwargs` + `setattr(self, key, value)` pattern (deliberately used so rule authors
and platform code can attach arbitrary metadata/fields) and found it at 5 sites across 3 files -
`rule.py` (`Fact`, `Rule`), `ftypes.py` (2 classes), `container.py` (`Collector`). This is the same
underlying tension already flagged as disqualifying for Codon in the Candidates section above
(mypyc needs the same staticness Codon does, just for class shape instead of rule-body typing) - it
just surfaces differently (a native-class layout error, not a parse/compile rejection).

A real workaround exists (a custom `__setattr__`/`__delattr__` per affected class routing known
literal names to native fields and everything else to a manual dict -
[mypy PR #19937](https://github.com/python/mypy/pull/19937),
[mypyc issue #1149](https://github.com/mypyc/mypyc/issues/1149)), but it would touch 5 call sites
across 3 public-API files (`rule.py`, `ftypes.py`, `container.py` - all under the "preserve existing
public APIs" rule in `CLAUDE.md`) just to make mypyc's native-class model tolerate a pattern the
engine uses by design. Decision (2026-10-26, user): don't do this - document mypyc as disqualified
by this pattern and move to Phase 3 (Nuitka), which preserves full Python semantics including
dynamic attributes by design and so isn't expected to hit this.

~~Add `mypyc` as a one-off dev-only build step (not committed to `pyproject.toml`'s normal build),
compile `src/knowledgenet` (already satisfies `disallow_untyped_defs = true` package-wide per
`001-...-DONE.md`) into a native extension, leave `autoins/rules/*.py` untouched/interpreted, run
the same workload. This isolates "engine-only, natively compiled" speedup in a real compiled
artifact (not just Phase 0's profile percentage) - the gap between this number and Phase 0's
engine-time percentage is the realistic ceiling for any engine-only compilation approach (mypyc,
Cython, or Rust+PyO3 equally), without yet touching rule-body typing.~~

### Phase 3 — Nuitka spike — **DONE (2026-10-26): compiles and runs correctly, but slower than CPython**

Installed Nuitka 4.3.1 ad hoc (`uv run --with nuitka`, not added to `pyproject.toml`) plus the
system `patchelf` package (`sudo dnf install -y patchelf` — standalone mode on Linux requires it;
user installed it). Compiled `test/perf/profile_engine.py` (same entrypoint used for every other
phase's timing comparison, not `rule_runner.py` directly, so numbers stay apples-to-apples across
phases) via `python -m nuitka --standalone`, unmodified `knowledgenet`/`autoins` source.

**Two flags were required beyond a plain `--standalone` build** - both forced by this engine's
design, not incidental: `--include-package=autoins` and `--include-package=knowledgenet`. Without
them the build "succeeds" but fails at runtime (`ModuleNotFoundError`), because rule modules are
discovered and `importlib.import_module()`'d dynamically from a user-supplied directory at runtime
(`scanner.load_rules_from_filepaths`) - Nuitka's static import-following from the entry script has
no way to see that `knowledgenet.decorator` (imported only from inside those dynamically-loaded,
never-statically-reachable rule files) is needed, so it isn't bundled unless told explicitly. This
is a real, generalizable packaging note for any Nuitka adoption of this engine, independent of the
benchmark result.

**Compatibility risk from the Open Questions section did not materialize:** the full
`opentelemetry-api`/`opentelemetry-sdk`/`opentelemetry-exporter-otlp` chain, including `grpcio` and
`certifi`, compiled and linked without issue (Nuitka's data-files plugin even picked up
`certifi/cacert.pem` and `grpc/_cython/_credentials/roots.pem` automatically). Build time ~2.5
minutes; `profile_engine.dist/` is 82 MB (42 MB binary + bundled interpreter/deps).

**Measured (apples-to-apples, same machine, same session, `--mode time` harness, 3 runs averaged):**

| claims | facts | CPython 3.14 (interpreted) | Nuitka (standalone, compiled) | delta |
|---|---|---|---|---|
| 300 | 604 | 3753.9 ms | 5102.4 ms | **+36% slower** |
| 500 | 1004 | 15382.7 ms | 20590.7 ms | **+34% slower** |

**Conclusion: Nuitka is a net regression for this workload, not a speedup**, consistently across
two scales. This goes further than the Candidates section's prediction of merely "modest" gains -
preserving full Python semantics (including this engine's pervasive dynamic `setattr`/duck-typing)
means Nuitka's compiled C code still has to emulate CPython's dynamic object model faithfully, and
that emulation overhead outweighs whatever it saves on bytecode dispatch. It's also plausible
CPython 3.14's own interpreter optimizations (this project's floor) are already fast enough on this
kind of workload that a generic AOT compile has nothing left to win. No further Nuitka tuning
attempted (e.g. `--lto`, PGO) - the gap is large and consistent enough at two scales that marginal
compiler-flag tuning is very unlikely to flip the sign, and that kind of tuning would anyway erode
the "zero source/config change" premise this phase was testing.

### Phase 4 — Codon feasibility check — **DONE (2026-10-30): disqualified, fast no, confirmed**

Downloaded the official Codon 0.20.5 Linux x86_64 release tarball directly from GitHub releases
(`exaloop/codon`) and extracted it to a scratch directory - not the `curl | bash` installer script,
to keep the download auditable before running anything from it. Ran its `codon` binary directly
against `rules/03_contract/eligibility_rules.py` unmodified, as the plan specified.

**Result: fails immediately, before reaching any of the expected semantic issues.**
`codon run rules/03_contract/eligibility_rules.py` →
`error: no module named 'knowledgenet.decorator'`. Tried `CODON_PATH=/home/amit/git/knowledgenet/src`
(Codon's own documented module-search mechanism, confirmed working against a trivial hand-written,
fully-typed probe package) - still `no module named 'knowledgenet'`, even for the bare `import
knowledgenet` with nothing else in it (an 11-line docstring-only `__init__.py`).

**Why, confirmed against Codon's own docs
([Python from Codon](https://docs.exaloop.io/integrations/python/python-from-codon/)):** Codon
draws a hard line between two kinds of imports - its own native-dialect modules (resolved via
`CODON_PATH`, and actually compiled) and "Python modules" (anything written as ordinary CPython
code, including every file in `knowledgenet` and `autoins`), which are reachable *only* via
`from python import ...` or the `@python` decorator. Both of those interop paths are documented to
run on an **embedded CPython runtime** - "instead of being compiled by Codon" - with values
marshalled across the boundary via `__to_py__`/`__from_py__`. There is no mechanism to have Codon
natively compile an existing, unmodified pure-Python package at all; the only bridge to one adds
CPython-boundary marshalling overhead on top of plain, uncompiled CPython execution.

**Conclusion:** this disqualifies Codon more fundamentally than the Context section anticipated -
it's not that `@ruledef`'s dynamic `setattr`/kwargs or duck-typed `this`/`ctx` fail Codon's static
type checker (that would require first getting knowledgenet's source *into* Codon's compiler, which
never happens); it's that nothing written as ordinary Python, compiled or not, is eligible for
Codon's compiler at all without a full rewrite into Codon's own restricted dialect - which is a port,
not a precompilation option, and so stays out of scope per the "no change to rule-author syntax"
hard constraint in Context. No further investigation attempted (e.g. forcing the interop path) -
it would, by the docs' own description, just be measuring uncompiled CPython through an extra
marshalling boundary, which can only be slower, never a precompilation win.

### Phase 5 — Rust/PyO3 micro-benchmark (narrow, not a port) — **DONE (2026-10-30)**

**Picked operation:** not `Factset.find()`/`_population()` as first suggested - its real hot-path
call always uses the default no-op filter (`lambda obj: True`), so it's really just "copy a
Python set," which is already a highly-optimized CPython C path with nothing for an FFI-crossing
Rust version to win against. Also ruled out `Collector.add`/`remove` (`container.py`) - both call
into arbitrary rule-author filter callables (`self._filter_obj`), so timing them would mostly
measure the cost of calling back into Python through the Rust boundary, not native-code speedup.

Picked instead: `Graph`'s ordinal-indexed bookkeeping (`core/graph.py`'s `_ordinal_tail`/
`_sorted_ordinals`, maintained by `_add_by_ordinal` and the matching half of `delete_element`) -
pure `bisect.bisect_left` + dict lookup + list insert/pop over plain ints, no rule-author callback
anywhere in it, and already known to be hot (this index backs every `Graph.add`/`delete_element`
call, i.e. once per fact insertion/deletion). Reimplemented just the index maintenance (not
`Element` construction/pointer relinking, which is Python-object-bound either way) as a small
`#[pyclass]` via PyO3 (`maturin develop --release`, scratch crate, not added to either repo) with
`insert(ordinal)`/`remove(ordinal)` methods structurally identical to the Python original, swapping
`_ordinal_tail`'s per-ordinal `Element` reference for a plain run-length counter (irrelevant to the
index-maintenance cost being measured).

**Method:** generated one fixed sequence of insert/remove operations (ordinals drawn from a
plausible distinct-ordinal range), ran it once-call-per-operation (not batched - matching how
`Graph.add`/`delete_element` would actually invoke it from otherwise-unmodified Python, so PyO3's
per-call crossing cost is paid in the number, not hidden) against a pure-Python class and the Rust
extension class, same op sequence, multiple scales.

**Measured:**

| ops | distinct ordinals | Python (best of 3) | Rust/PyO3 (best of 3) | speedup |
|---|---|---|---|---|
| 100,000 | 500 | 7.03 ms | 5.41 ms | 1.31x |
| 400,000 | 2,000 | 30.96 ms | 21.18 ms | 1.47x |
| 1,000,000 | 20,000 | 175.71 ms | 104.88 ms | 1.68x |
| 2,000,000 | 50,000 | 672.40 ms | 450.06 ms | 1.49x |

**Conclusion: a real but modest win, ~1.3-1.7x, not the order-of-magnitude some expect from "port
to Rust."** Two things cap it: (1) each operation already pays one Python-to-native call crossing
through PyO3, comparable in overhead to the Python method call it replaces, so the per-call tax is
paid on both sides, not eliminated; (2) `list.insert`/`.pop` on the Python side is already a C
implementation (CPython's own `listobject.c`), so there's no interpreted-vs-compiled gap on that
part specifically - the win comes mostly from the dict hashing and bisect comparisons running as
native code instead of bytecode. No comparison point against Phase 2's mypyc ceiling was possible -
Phase 2 was disqualified before producing any benchmark number (see its section above), not just a
lower number - so this phase's result stands on its own rather than cross-checking against it.
Scaling this finding to the whole engine would require actually porting `Graph` (and everything
structurally like it) to Rust, which is explicitly out of scope per this plan's own "no engine
port" boundary (see Explicitly out of scope) - a real, larger decision for a future plan, not
something this spike should extrapolate into a recommendation on its own.

### Phase 6 — Comparative writeup and recommendation — **DONE (2026-10-30)**

| Candidate | End-to-end speedup | Rule-author syntax constraint | Compatibility risk | Packaging/deployment delta | Reversibility |
|---|---|---|---|---|---|
| **PyPy** | Not measured - disqualified before benchmarking | None | **Disqualifying**: no PyPy build targets this project's 3.13+ floor, from any source (latest is 3.12) | n/a | n/a |
| **mypyc** | Not measured - disqualified before benchmarking | None for rule bodies (only engine internals compiled) | **Disqualifying**: native classes have no `__dict__`; `Rule`/`Fact`/`Collector`'s post-construction dynamic attributes (by design) break at runtime, not compile time | Dev-only build step, not in normal `pyproject.toml` build | High in principle (opt-in build step) but blocked before reversibility mattered |
| **Cython** | Not run | Same as mypyc | Same disqualification as mypyc (native extension types, same `__dict__`-less default) | n/a | n/a |
| **Nuitka** | **Measured, negative: 34-36% *slower*** than plain CPython at 300/500 claims | None - full Python semantics preserved | Low - the `opentelemetry`/`grpc` chain compiled without issue; needs `--include-package=knowledgenet` since rules are discovered dynamically at runtime, outside static import-following | New build artifact (standalone binary + bundled runtime, 82 MB dist for this workload), ~2.5 min build | Fully reversible (build step only, no source changes) but moot given the regression |
| **Codon** | Not measured - disqualified before any benchmark was possible | Would require a full rewrite into Codon's own dialect - violates the hard constraint outright | **Disqualifying, structurally**: no mechanism to compile an unmodified pure-Python package at all; only route in is `from python import`/`@python` interop, which runs on an embedded, uncompiled CPython | Would be a parallel codebase, not a build step | None - not adoptable without the rewrite the constraint rules out |
| **Rust + PyO3** | **Measured, positive but narrow: 1.3-1.7x** on one isolated hot bookkeeping function (`Graph`'s ordinal index), not measured end-to-end | None for rule bodies; would require porting specific engine-internal functions (not rule-author code) to Rust | Low for the specific function tested; unknown/unassessed at full-engine scope | Would add a Rust toolchain + PyO3/maturin build step per ported function - more invasive than any other candidate per unit of code touched | Incremental in principle (one function at a time) - the only candidate where that's structurally true |

**Recommendation: no precompilation option clears the bar as a drop-in adoption today.** Four of
five candidates are disqualified or net-negative without any source changes; the fifth (Rust/PyO3)
shows a real but modest win confined to one isolated, non-representative-of-the-whole-engine
function, and scaling it up would mean actually porting engine internals - a genuinely separate,
larger effort (already flagged as "the separate, larger effort discussed in conversation" in
Context, and explicitly out of scope here per Explicitly out of scope below). This confirms Phase
0's own finding from the other direction: `autoins`'s rule bodies were never where the time went
(under 1% of runtime), so no tool whose speedup mechanism depends on compiling rule-author code
(mypyc's ceiling measurement, Cython, Codon) was ever going to move the needle even if each were
otherwise compatible - and the two candidates that *do* preserve full Python/engine-internal
semantics (PyPy, Nuitka) either can't run on this project's Python floor or actively regress
performance. If a decisive speedup is still wanted, the two live paths are: (a) finish plan 003's
own Phase 5 (incrementally maintained per-when-clause populations in `Factset`/`Session`) - already
identified as the clearest remaining algorithmic lever, no new tooling required; or (b) a real,
scoped Rust port of specific engine-internal hot spots (`Graph`, `Factset`'s indexes, `Collector`),
informed by this phase's 1.3-1.7x per-function ceiling - but that is new, larger-scope work, not a
continuation of this exploratory plan.

## Explicitly out of scope

- Actually porting `knowledgenet`'s engine or `autoins`'s platform code to Rust — that's the
  separate, larger effort discussed in conversation; this plan only produces the micro-benchmark
  data point (Phase 5) that such a plan would need as justification.
- Requiring rule authors to add type annotations, convert lambdas to typed functions, or otherwise
  change how rules are authored — ruled out by the hard constraint in Context.
- Any change to `autoins/rules/*.py` content or behavior — every phase runs the existing rules
  unmodified; only the execution environment (interpreter/compiler) changes per phase.
- Production CI integration of any candidate — this plan produces a recommendation, not a shipped
  build pipeline.

## Open questions / risks

- `opentelemetry-exporter-otlp`'s `grpcio` dependency is the most likely compatibility blocker for
  both PyPy (Phase 1) and Nuitka (Phase 3) — if it fails, decide per-phase whether to benchmark with
  tracing disabled (`OTEL_TRACES_EXPORTER` unset/none) as a fallback, and flag that the comparison is
  then incomplete rather than silently presenting it as equivalent.
- Phase 0's profiling split could come back less lopsided than the conversation assumed (e.g. engine
  bookkeeping is actually 40%+ of runtime) — if so, Phase 2's mypyc ceiling and Phase 5's Rust
  micro-benchmark become more decision-relevant than Phases 1/3, and the plan's emphasis should
  shift accordingly rather than mechanically running every phase regardless of what Phase 0 shows.
