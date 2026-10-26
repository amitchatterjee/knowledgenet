# Explore precompilation options for faster rule evaluation

Status: **PAUSED (2026-10-26)** — Phase 0 DONE (2026-10-17); Phases 1-2 DISQUALIFIED, Phase 3
DONE-NEGATIVE (all 2026-10-26); paused before Phase 4 (Codon), to resume later. This was a
research/spike plan: each phase was meant to produce a measurement and a go/no-go judgement, not
shipped code. Phase 0 ran as intended, but what it found was urgent and actionable enough that it
turned into real shipped fixes instead of just a data point — see
`003-2026-10-17-rete-engine-performance-fixes.md`, which is where that work actually lives (also
currently paused). Phase 1 (PyPy) was disqualified on resumption without running a benchmark; Phase
2 (mypyc) was disqualified after a real compile attempt surfaced a structural incompatibility; Phase
3 (Nuitka) compiled and ran correctly but measured **36%/34% slower than plain CPython** at 300/500
claims, two-for-two - a real negative result, not a blocker (see their sections below). One
incidental finding from Phase 2 (a scanner.py reflection fix) was kept as a permanent,
independently-useful fix regardless. So far, nothing beats the plain CPython 3.14 baseline. To
resume: start at Phase 4 (Codon feasibility check, expected fast disqualification per the
Candidates section), then Phase 5 (Rust/PyO3 micro-benchmark) and Phase 6 (writeup) - Cython
(candidate 3) stays un-run, it shares mypyc's Phase 2 disqualification.

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

### Phase 4 — Codon feasibility check (short, likely a fast no)

Attempt to run Codon's compiler against one small, already-simple rule file (pick the smallest
ruleset, e.g. `03_contract/eligibility_rules.py`) without modification. Expect and document the
specific incompatibilities (dynamic `setattr`-based kwargs, `@ruledef` decorator machinery,
duck-typed `this`/`ctx`) rather than attempting workarounds — this phase exists to turn "probably
disqualified" into a documented, specific reason, in case the question comes up again later.

### Phase 5 — Rust/PyO3 micro-benchmark (narrow, not a port)

Not a port of the engine. Pick one concrete, isolated hot operation identified by Phase 0 (likely a
`FactSet` indexing/lookup or alpha-node matching operation) and reimplement *just that function* as
a small Rust extension via PyO3 (`maturin develop`), called from otherwise-unmodified
`knowledgenet` internals. Microbenchmark that one function in isolation (Python version vs.
PyO3-backed version) to get a real native-code-speedup number for engine-internal work, independent
of Phase 2's mypyc ceiling — this cross-checks whether mypyc's native-compilation ceiling is close
to Rust's, or whether Rust buys meaningfully more for this kind of pointer-chasing/hashing code.

### Phase 6 — Comparative writeup and recommendation

Table of all five candidates against the Design section's decision criteria, filled in with Phases
0-5's actual numbers (not estimates). Explicit recommendation: most likely either "PyPy, zero-code-
change adoption, re-evaluate if dependency compatibility is a blocker" or "no precompilation option
clears the bar without violating the untyped-rules constraint, revisit if that constraint changes."
This phase's output is the input to a future implementation plan — it does not itself change any
source file in `knowledgenet` or `autoins`.

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
