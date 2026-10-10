# Explore precompilation options for faster rule evaluation

Status: **PROPOSED — not started**. This is a research/spike plan: each phase produces a
measurement and a go/no-go judgement, not shipped code. No phase here commits the project to a
rewrite; the output is a recommendation that a separate, later implementation plan would act on.

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

### Phase 0 — Profiling baseline (no tooling changes)

Run `autoins` under `cProfile` (and/or `py-spy` for sampling, if installed) against its existing
test data, and break down time spent in:
- `knowledgenet/core/graph.py`, `factset.py`, `node.py` (engine bookkeeping), vs.
- time attributed to the actual `matches=`/`then=` callables defined in `autoins/rules/*.py`.

This is the number the whole plan hinges on — it either confirms or corrects the "rule bodies
dominate" premise from the prior conversation before any tool is evaluated. Record the split as a
percentage and call out which specific rules/rulesets are hottest (useful context for later phases
even if the overall split is lopsided).

### Phase 1 — PyPy spike

Install `pypy3` (matching the project's 3.13+ floor), create a PyPy-backed venv for `autoins` +
local-source `knowledgenet` (same `[tool.uv.sources]` path-dependency setup as the CPython venv,
or a plain `pypy3 -m venv` if `uv` + PyPy interact badly — check first), run the same autoins
workload, compare wall-clock against Phase 0's baseline. Check `opentelemetry-sdk`/
`opentelemetry-exporter-otlp` import and basic span export work under PyPy before trusting the
timing (if they don't, note whether tracing can be disabled for the benchmark without invalidating
the comparison). No source changes to `knowledgenet` or `autoins` — the entire point is "does this
work and get faster with zero code changes."

### Phase 2 — mypyc ceiling measurement

Add `mypyc` as a one-off dev-only build step (not committed to `pyproject.toml`'s normal build),
compile `src/knowledgenet` (already satisfies `disallow_untyped_defs = true` package-wide per
`001-...-DONE.md`) into a native extension, leave `autoins/rules/*.py` untouched/interpreted, run
the same workload. This isolates "engine-only, natively compiled" speedup in a real compiled
artifact (not just Phase 0's profile percentage) — the gap between this number and Phase 0's
engine-time percentage is the realistic ceiling for any engine-only compilation approach (mypyc,
Cython, or Rust+PyO3 equally), without yet touching rule-body typing.

### Phase 3 — Nuitka spike

Compile `autoins`'s `rule_runner.py` entrypoint plus `knowledgenet` and `autoins` source as a
standalone Nuitka executable (`--standalone` or `--onefile`), unmodified source, run against the
same workload. Note build time and binary size alongside the runtime number — both are real costs
of this option even if runtime improves. Confirm the `opentelemetry-*` dependency chain actually
compiles (Nuitka's C-extension/compiled-dependency support is the main practical risk here, not
semantics).

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
