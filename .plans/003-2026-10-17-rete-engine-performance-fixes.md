# Fix the RETE engine's super-linear scaling, found via Phase 0 profiling

Status: **PAUSED** (2026-10-26) — Phases 1-4 and 6 DONE and verified (each independently tested,
measured, and confirmed against `autoins`). Phase 5 identified, not started (see its section
below for why - the investigation that started it led to Phase 6 instead). Deliberately paused
here, not abandoned: work is shifting to `002-2026-10-10-precompilation-options-exploratory-plan.md`'s
precompilation spikes (PyPy/mypyc/Nuitka/Codon/Rust). To resume this plan later, start from Phase
5's "Investigated, not yet started" note and the "Time-vs-facts relationship" section below - both
point at the same fix (incrementally maintained per-when-clause populations in `Factset`/
`Session`), which remains the clearest lever on the engine's residual super-linear scaling.

## Context

This plan grew directly out of `002-2026-10-10-precompilation-options-exploratory-plan.md`'s
Phase 0 (profiling `autoins` to establish the real engine-vs-rule-body time split before
evaluating any precompilation option). That profiling, done with the harness at
`knowledgenet-examples/autoins/test/perf/`, immediately surfaced something more urgent and more
actionable than anything on 002's original list: `Service.execute()` wall-clock time scaled
roughly **cubically** with claim count (100→150→200 claims: 3.78s → 14.87s → 40.27s), and 500
claims did not complete at all. A cubic blowup at these scales isn't a precompilation question -
it's a concrete algorithmic bug, almost certainly worth fixing regardless of what (if anything)
comes out of 002's PyPy/mypyc/Nuitka/Codon spikes.

Four independent root causes were found this way, each confirmed by profiling before being touched
and re-confirmed by profiling afterward, each a genuine `O(n)`-or-worse-per-call cost hiding behind
"recompute from scratch" code that had no incremental memoization - the same structural pattern
each time, at a different layer of the engine. See 002's Phase 0 section for the premise this work
revised: rule-author `when`/`then` code is **not** where the time goes for this ruleset (under 1%,
measured in Phase 4's verification) - the engine's own bookkeeping is ~77%+ of total runtime, even
after all four fixes below.

## Design

Methodology, applied identically to all four phases: profile first (never assume), read the actual
calling code before designing a fix (not just the hot function in isolation - several of these
fixes turned out to depend on invariants enforced *elsewhere*, like `Graph.add`'s FIFO tie-breaking
determining RETE execution order), add tests for the changed function if none existed (none did,
for any of the four), verify `mypy src/knowledgenet` clean and the full `knowledgenet` unit suite
green, then rebuild `autoins`'s venv against the patched engine and confirm its own test suite
(checksum-based expected-output comparisons) still passes before measuring the real-world impact
with the Phase 0 harness.

**Order-of-operations constraint carried through every phase:** `knowledgenet-examples/autoins`'s
rule_runner.py and `knowledgenet`'s own `Session`/`Graph` make insertion order, and specifically
*ties* in `rule.order`, into real, observable behavior - `Graph.add()` breaks ordinal ties by pure
FIFO insertion order, and nodes sharing an ordinal execute in that same order. Every fix below that
touches ordering (`perm.py`'s rewrite, `graph.py`'s indexed insertion, `session.py`'s `_delete_facts`
reordering) was designed and tested against this constraint specifically, not just against
"produces the same set of results."

### Phase 1 — `core/perm.py`: `combinations()`'s generate-then-filter — DONE

**Found:** `combinations(ll, include_only)` built the full cartesian product of all `when`-clause
populations, then scanned every tuple checking list-membership (`O(k)` per check, `include_only`
was a `list`) to keep only tuples containing >=1 newly-inserted fact. For a rule with multiple
large-population `when` clauses this does `O(P)` work (`P` = full product size) to produce a much
smaller output.

**Fix:** replaced with a recursive construction (`_append_matching`/`_append_all`) that walks
`ll[0], ll[1], ..., ll[n-1]` in their native order exactly as `cartesian()` does, short-circuiting
to unfiltered construction (`_append_all`) the moment a prefix already contains a qualifying
element - `O(output size x n)` instead of `O(P x n)`, and critically, **the exact same output
order** as the original generate-then-filter (verified by hand-derivation and by an independent
`itertools.product`-based reference implementation in the test suite, not by comparing against the
old code). An earlier design (grouping output by "leftmost qualifying position") was rejected after
the user caught that it changes emission order - this was the point at which the order-preservation
constraint above was established as load-bearing, via tracing `Graph.add`'s FIFO tie-break and
`Session._minimum`'s "first element of a same-ordinal batch wins ties" behavior.

**Verified:** `mypy` clean. `test/unit/test_perm.py` (new, 12 tests) covers order preservation
(including the `{1,2,3}x{1,2,3}` hand-derived case), the duplicate-type/self-join case (same Fact
type at two `when`-clause positions - confirmed no special-casing needed, positions are independent
draws from the same pool), multiple simultaneous new facts, and edge cases (empty `ll`, no match).
101 `knowledgenet` unit tests pass (89 pre-existing + 12 new). `autoins`'s 5 tests pass against the
rebuilt engine. Not the dominant cost at any scale profiled during this phase - included as a
correct, never-regressing fix and a prerequisite for reasoning clearly about the phases that
followed.

### Phase 2 — `core/tracer.py`: always-on return-value stringification — DONE

**Found:** `trace()`'s `wrapper()` called `normalize_attribute(ret, trace_details_val)` -
stringifying the return value via `str()`, hitting custom `__str__`/`__repr__` on `Node`/`Request`/
etc. - whenever `ret is not None`, **regardless of whether tracing was actually active**.
`trace_ctx.set_attribute()` on the no-op `PassThruTraceContext` correctly discarded the result, but
the expensive part had already run. At `trc_level=0` (autoins's default), this was pure waste on
every traced call.

**Fix:** skip the normalize-and-discard entirely when the call wasn't traced
(`trace_ctx is not _PASS_THRU`); reuse one stateless `PassThruTraceContext` singleton instead of
allocating one per disabled call; cache the deferred `knowledgenet.service` contextvar import
(needed to break the `service.py` <-> `tracer.py` circular import) after its first resolution
instead of re-importing on every call.

**Verified:** `mypy` clean. `test/unit/test_tracer.py` (new, 9 tests), including one that patches
`normalize_attribute` and asserts it's never called when tracing is below the decorator's level -
the actual regression this fix closes. 110 unit tests pass. `autoins` 5/5.

**Measured (same `test/perf/profile_engine.py` harness, before -> after this phase alone):**
100 claims 3.78s -> 2.13s (1.77x), 150: 14.87s -> 9.38s (1.59x), 200: 40.27s -> 27.42s (1.47x). A
real constant-factor win, not the structural cause - confirmed by re-profiling: scaling stayed
cubic-ish, and `graph.py:add` emerged as the new #1 cost.

### Phase 3 — `core/graph.py`: `Graph.add()`'s O(graph size) linear scan — DONE

**Found:** `add()` scanned from `self.first` to find the correct `ordinal`-sorted insertion point
(and, with no `self.last` pointer at all, scanned the *entire* list just to discover the tail when
appending). 24,304 calls for a 150-claim run, each `O(current graph size)` - the direct cause of
the cubic-ish blowup, since call count and per-call cost both grow with the graph's size.

**Fix, scoped to the no-comparator (default, `rule.order`-based) path only:** added
`self.last: Element | None` (O(1)-maintained tail pointer), `self._ordinal_tail: dict[int, Element]`
(the tail of each distinct ordinal's contiguous run - same-ordinal elements are always contiguous
by construction), and `self._sorted_ordinals: list[int]` (the small set of distinct ordinals,
`bisect`-maintained). Repeat-ordinal inserts (the overwhelming majority - `rule.order` only takes a
handful of distinct values across a whole ruleset) splice in `O(1)` right after the bucket's tail;
a genuinely new ordinal costs `O(log k)` to locate via `bisect` plus `O(1)` to splice (`k` = number
of distinct ordinals, a small constant, not `n`). The `node_sorter`/comparator path (arbitrary
2-argument comparator, tested separately in `test_comparator_based_insert`) was deliberately left
as the original `O(n)` scan - no evidence anywhere that it's ever hot, and a general comparator
can't be indexed this way without a materially different structure (skip list / balanced tree).

**Bugs caught during implementation, not shipped:** accidentally reintroduced
`from __future__ import annotations` (removed deliberately in `001-...-DONE.md` Phase 3 as
redundant under Python 3.14's PEP 649) - caught against that plan's own history and reverted before
running anything. A `mypy` `no-redef` error from a shadowed local in the new `_add_scan` helper,
same class of issue Phase 2 of `001-...-DONE.md` had already fixed once in this exact function -
fixed by renaming, not by re-litigating.

**Verified:** `mypy` clean. `test/unit/test_graph.py` +5 tests: same-ordinal ties with *distinct*
objects (the existing `test_next_elements` used identical int placeholders, which can't actually
distinguish insertion order), ties interleaved with other ordinals, delete-the-tail-then-reinsert,
delete-the-only-element-of-an-ordinal-then-reinsert-a-neighbor, and `self.last` tracking through
add/delete. 115 unit tests pass. `autoins` 5/5, including checksum-matched expected outputs
(confirms node execution order, not just the result set, is unchanged).

**Measured:** 100: 2.13s -> 0.665s (3.2x), 150: 9.38s -> 2.23s (4.2x), 200: 27.42s -> 4.99s (5.5x).
`graph.py:add` dropped out of the hot-function list entirely on re-profile. `session.py:
_update_facts`'s full graph scan (`reset_whens`, 3M+ calls at 200 claims) became the new #1 engine
cost - the same structural pattern one layer up.

### Phase 4 — `core/session.py`: `_update_facts`/`_delete_facts`'s full graph scans — DONE

**Found:** both methods reset a cursor to `self.first` (`new_cursor` always does this when no
`element` is passed) and walked **every node currently in the graph**, checking
`node.when_objs`/`reset_whens` for overlap with the changed facts - on every single update or
delete, anywhere. 636 `_update_facts` calls at 200 claims, ~4,724 nodes scanned per call on average
(the graph's size at that point) - `O(graph size)` per call, called `O(n)` times.

User's framing going in: creates/deletes are more common than updates in RETE generally, but this
specific ruleset exercises updates heavily too (`compute_collision_payment_rhs`,
`select_action_rhs` both call `update()`), and `_delete_facts` has the *identical* shape of problem
- so the fix needed to serve both, via one shared structure, kept cheap on the `_add_facts` path
(the actually-more-common one) rather than optimizing update at the expense of create.

**Fix:** `self._fact_to_elements: dict[Hashable, set[Element]]` - a reverse index from fact to the
graph `Element`s whose node references it, maintained in `_index_node`/`_deindex_node` (called from
`_add_facts` on node creation, and from `execute()`'s `run_once` cleanup and `_delete_facts` on node
removal). `_update_facts` now looks up only the affected elements (`O(sum of per-fact bucket
sizes)`, visited in any order - the min-reduction over `reset_whens` results is commutative, and
`reset_whens` is already a safe no-op for any node not actually touching the updated facts, so
skipping unaffected nodes changes nothing observable). `_delete_facts` needed more care: its
"jump to the deleted element's successor when it's the current `new_leftmost`" branch **is**
order-sensitive, so affected elements are processed sorted by `.weight` - this exactly reproduces
what the original full graph-order scan visited, restricted to the subset that mattered (a provable
equivalence: elements the old scan skipped over never touched `new_leftmost` either, so omitting
them from the walk changes nothing; the remaining elements are visited in the same relative order
either way). Also fixed: `_update_facts`'s recursive-call `execution_node` argument used to be
whatever node the old full scan happened to land on last (which, since the scan always ran
`self.first` to the end, was really just "whatever is at the tail of the whole graph" -
accidental-looking, not a deliberate rule, but real existing behavior) - now computed directly as
`self.graph.last.obj` (O(1), using Phase 3's tail pointer) instead of as a scan byproduct, with
identical results.

**Verified:** `mypy` clean. `test/unit/test_rule_chaining.py` +1 test
(`test_delete_multiple_facts_in_one_batch_leaves_untouched_node_reachable`): a single `then=`
deleting two facts in one batch (`_delete_facts` called with `len(deduped_deletes) > 1`, a shape no
existing test exercised), with an untouched third rule's node positioned *between* the two deleted
nodes in graph order - checks that the untouched node still fires. (Tried removing the weight-sort
to confirm this test would catch that specific regression - it didn't, because the deleting rule's
own node wasn't among the deleted elements in this construction, so the order-sensitive branch
never triggered; the sort's correctness rests on the equivalence argument above, not on this test
alone, and the test stands as real coverage of the previously-untested multi-element-batch shape
either way.) 116 unit tests pass. `autoins` 5/5.

**Measured:** 200: 4.99s -> 2.16s (2.3x further). 500 claims completed for the first time at any
stage of this plan - 29.7s, versus never finishing (60s+ timeout) at every prior stage, including
right after Phase 3.

### Phase 5 — `Factset.find()` / `_get_matching_objs()`'s full re-scan — IDENTIFIED, NOT STARTED

Profiling 300 -> 500 claims (after Phase 4) showed total `Node` objects created growing ~`O(n^2)`
(93,604 -> 256,004) and `combinations()`'s call-cost growing even faster (~`O(n^2.9)`), with overall
wall-clock still clearly super-linear (500 claims: 29.7s, not the ~linear-from-200 number a flat
cost would predict). Root cause: `Session._get_matching_objs` calls `Factset.find(when.of_type,
group=when.group)` **from scratch** on every single `_add_facts` call. For `autoins`'s
`pay_on_no_action`/`select_action` rules (`when=Collection(group='action-collector', ...)`), that
query returns *every* request's `Collector` - correct and necessary by design, since each rule
genuinely needs one node per request - but the cost of discovering "which Collector is new this
round" is paid as a fresh `O(current population)` scan+filter, repeated roughly once per claim-level
event. Same missing-incremental-memoization pattern as Phases 3 and 4, one layer further up (in
`Factset`, not `Graph`/`Session`) - not yet designed. Likely shape of a fix: maintain each
when-clause's (type, group) population incrementally (update on insert/delete) rather than
recomputing via `find()`'s full scan every `_add_facts` call - mirrors Phase 3/4's approach closely
enough that it's probably the highest-leverage next step, but needs its own read-the-actual-callers
pass (`Factset.add_facts`/`del_facts`/`update_facts`, and whatever else calls `find()` directly)
before designing anything, per this plan's own methodology.

**Investigated, not yet started:** before implementing the above, re-profiled per this plan's own
"profile first, never assume" rule - `perm.py`'s `combinations()`/`_append_matching`/`_append_all`
turned out to be negligible at this point (~0.1% of total runtime, absent from a 300-claim
profile's top 15 entirely). The real cost at that moment was `@trace()`'s per-call overhead, not
`Factset.find()`'s re-scan - see Phase 6 below, done instead. Phase 5's actual fix (incrementally
maintained per-when-clause populations) is still unimplemented and, per the scaling analysis in
"Time-vs-facts relationship" below, is now more clearly necessary than ever: the engine's
time-vs-facts relationship is still measurably super-linear even after Phase 6.

### Phase 6 — `core/tracer.py`: `@trace()`'s per-call overhead on RETE-internal hot paths — DONE

**Found:** investigating Phase 5's listed next step above before implementing it surfaced a
bigger, unrelated cost. `@trace()`'s `wrapper()` (tracer.py) was ~41-53% of total engine time
across tens of millions of calls, *even with tracing fully disabled* (`trc_level=0`, `autoins`'s
default) - every `@trace()`-decorated call pays for an extra stack frame, two `ContextVar.get()`
reads, a `trace_context_factory()` call, and a context-manager `__enter__`/`__exit__` pair before
it can determine there's nothing to trace. Nearly all of the call volume came from three
functions decorated at the engine's innermost, hottest layer: `Node.execute`/`Leaf.execute`/
`Node._execute_thens` (`node.py`) - decorated with bare `@trace()`, defaulting to level=1, the
"application code" band per `docs/rule-service.md`'s own convention, despite being RETE-internal
- plus `Collector.add`/`remove` (`container.py`, already correctly tagged level=14) and
`Graph.next_element` (`graph.py`, already correctly tagged level=13, called once per node
traversal in `session.py`'s main execution loop).

**Fix:** commented out (not deleted - restorable with a one-line uncomment if ever needed for
engine-internal debugging) the `@trace()` decorators on exactly those five call sites. Didn't
touch `tracer.py`'s mechanism itself, and left every other `@trace()` site alone (`session.py`
level 11, `factset.py` level 12, `node.py`'s `reset_whens` level 13, `graph.py`'s
`next_elements`) - none of them individually contributed a significant share of the call count.

Also fixed incidentally: removing `@trace()` from `Node.execute` exposed a latent type error
`mypy` couldn't previously see - the decorator's loose `Callable` signature had been erasing the
wrapped function's real parameter types from type-checking (same class of issue Phase 5's
`_population()` work ran into). `Node.execute`'s `facts` parameter was annotated `set` but its
only call site (`session.py`) passes a `Factset`, matching `helper.factset(ctx)`'s documented
return type - corrected to `Factset`.

**Verified:** `mypy src/knowledgenet` clean. 123/123 `knowledgenet` unit tests pass (no new tests
needed - comment-only and type-annotation changes to already-tested code paths). `autoins`
rebuilt (`uv sync --reinstall-package knowledgenet`), 5/5 tests pass.

**Measured** (`test/perf/profile_engine.py`, same harness, clean data each run):

| claims | before Phase 6 | after node.py/container.py | after graph.py (final) |
|---|---|---|---|
| 300 | 6.55s | 4.86s (-26%) | 3.69s (-44%) |
| 500 | 27.4s | 19.1s (-30%) | 15.8s (-42%) |

`wrapper()` call count at 300 claims: 11.67M -> 2.86M (after node.py/container.py) -> 82,958
(after `graph.py`'s `next_element`, which alone had been 97% of what remained). Combined effect:
roughly 1.75-1.8x faster than immediately before this phase.

## Overall measured result (Phases 1-4 combined, clean re-measurement, same harness/seed)

| claims | original baseline | after Phases 1-4 | speedup |
|---|---|---|---|
| 100 | 3.78s | 0.33s | 11.6x |
| 150 | 14.87s | 0.92s | 16.2x |
| 200 | 40.27s | 2.40s | 16.8x |
| 500 | never completed | ~30s | infeasible -> feasible |

Speedup grows with scale, as expected - the fixes removed costs that were themselves scaling with
graph/population size, so the win compounds. The remaining non-linearity is Phase 5's unfixed
`Factset.find()` re-scan.

**Engine vs. application time, reclassified by source repo from the saved `.prof` files (300 and
500 claims, after Phases 1-4):** `knowledgenet` (engine) ~77%, stdlib/Python overhead (mostly
`logging.debug`/`ContextVar.get` calls the engine triggers internally, not caused by `autoins`)
~22%, `autoins` application code (both rule bodies *and* its own platform code - `entities.py`,
`fact_io.py`) **under 1%**. This inverts the premise `002`'s Context section started from (that rule
bodies dominate runtime) - see that plan's Phase 0 section for the resulting revision.

### Current state after Phase 6 (clean re-measurement, same harness/seed)

| claims | original baseline (pre-Phase 1) | current (Phases 1-6) | speedup |
|---|---|---|---|
| 100 | 3.78s | 0.217s | 17.4x |
| 150 | 14.87s | 0.585s | 25.4x |
| 200 | 40.27s | 1.094s | 36.8x |
| 300 | not part of original baseline sweep | 3.690s | - |
| 400 | not part of original baseline sweep | 8.072s | - |
| 500 | never completed (60s+ timeout) | 15.797s | infeasible -> feasible |

Speedup keeps growing with scale, consistent with the pattern noted above - but see the next
subsection: growth with scale is itself evidence the relationship still isn't linear, even now.

### Time-vs-facts relationship: still measurably super-linear (disclaimer-laden linear fit)

Asked (by the user) to characterize the current `time = coefficient * facts + base` relationship
*assuming it's linear*. Least-squares fit over the six points above (facts = 2*claims + 4):
**coefficient ~= 0.0188 s/fact, base ~= -5.50s**, R^2 ~= 0.90.

**This "fit" should not be used for anything - it's recorded here only as a documented answer to
the question actually asked, not as a model to extrapolate from:**
- The base term is negative (~-5.50s), which is physically impossible (time can't be negative at
  zero facts). That alone is the signature of forcing a line through data that actually curves.
- Residuals (`y - y_hat`) go +, +, -, -, -, + across the six points in increasing-facts order - a
  clean U-shape, the textbook fingerprint of a straight line fit to convex (upward-curving) data.
- Doubling facts from 404->804 gives 7.4x the time (1.09s -> 8.07s), not ~2x; a linear
  relationship would predict ~2x. Even a quadratic relationship would only predict ~4x.
- This matches Phase 5's own finding (never fully resolved - see that phase's "Investigated, not
  yet started" note above): Node creation and matching cost were measured growing ~O(n^2) to
  O(n^2.9) before Phase 5's partial (~10%) mitigation, and Phase 6 only removed a constant
  per-call cost - it did nothing to the underlying growth exponent.

**Conclusion:** the relationship is not linear, and treating it as such (e.g. to predict time at
claim counts beyond what's been measured) would significantly underestimate actual cost at scale.
Phase 5's originally-identified fix - incrementally maintained per-when-clause (type, group)
populations in `Factset`/`Session`, instead of `Factset.find()`'s full re-scan on every
`_add_facts` call - remains the candidate that targets this curvature directly, and is now the
clearest remaining lever if further scaling work is wanted.

## Explicitly out of scope

- `002`'s PyPy/mypyc/Nuitka/Codon/Rust spikes - this plan's findings don't replace that
  exploration, but do suggest the highest-leverage next step is Phase 5 above, not any of those
  (rule bodies are under 1% of cost; compiling or re-interpreting them has a low ceiling regardless
  of tooling).
- Indexing the comparator (`node_sorter`) path in `Graph.add()` - no evidence it's ever hot;
  revisit only if profiling ever shows otherwise.
- Any change to `autoins/rules/*.py` or `autoins/src/autoins/*.py` - every fix is engine-side
  (`knowledgenet`); `autoins` was only rebuilt against the patched engine and used as the
  real-world verification harness, never edited.

## Verification

Repeated identically for each phase (see each phase's own Verified/Measured text above for the
specific numbers): `mypy src/knowledgenet` clean; full `knowledgenet` unit suite green; `autoins`
rebuilt against the patched engine (`uv sync --reinstall-package knowledgenet`) with its own 5-test
suite (checksum-based expected-output comparisons) green; `test/perf/profile_engine.py` timing
and/or profile run to measure real-world impact and confirm the next bottleneck before moving on.
