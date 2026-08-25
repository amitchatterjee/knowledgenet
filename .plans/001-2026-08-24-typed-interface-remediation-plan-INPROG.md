# Add a typed interface and modernize type hints to Python 3.14 idioms

Status: **INPROG** — plan only, implementation not started.

## Context

The engine has no enforced typed interface: there is no type checker in dev dependencies, no CI
workflow that runs one (or anything else — see below), and annotation coverage across
`src/knowledgenet/` is inconsistent — some modules (`helper.py`, most of `rule.py`/`ftypes.py`/
`container.py`/`core/graph.py`) are well-annotated with modern syntax, while the most-called
surface (`controls.py`, `factset.py`, `service.py`, `node.py`) has none at all. Three separate but
related debts were identified and are addressed together here, since fixing (2) without (1) has no
staying power and (3) can't be told apart from (2) without a checker:

1. **No typed interface** on the public API (`Service.execute`, `Factset.find`/`add_facts`/
   `update_facts`/`del_facts`, `controls.insert`/`update`/`delete`, etc.) — callers get no
   IDE/static feedback on the library's actual entrypoints.
2. **Old-style typing left over pre-3.10/3.9**: `typing.Union[...]` (`ruleset.py`, `scanner.py`,
   `core/session.py`), `typing.List` (`util.py`), and `typing.Callable`/`typing.Sequence` used
   instead of `collections.abc.Callable`/`collections.abc.Sequence` (`container.py`, `rule.py`,
   `ftypes.py`, `core/file_trace_exporter.py`), sitting alongside other modules in the same package
   that already use PEP 604 `X | Y` and builtin generics. Project requires Python 3.13+ (3.14
   recommended per `docs/readme-development.md`), so there's no compatibility reason left for any of
   this.
3. **Not-best-practice types where annotations do exist** — implicit-Optional parameters
   (`param: str = None` with no `| None` in the annotation), mutable default arguments, and at least
   one outright typo (`-> tuple[Element:int]`, a `:` where a `,` was meant).

**Baseline, measured by actually installing and running mypy 2.3.1 (`pip install mypy` into
`.venv`, not in dev deps yet — see Phase 1) against `src/knowledgenet`:**

- Default mypy (no config, no strict flags): **44 errors across 10 of 20 source files**.
- `mypy --strict`: **314 errors across 18 of 20 source files** — most of the delta over the default
  run is `no-untyped-def`/`no-untyped-call` cascades, not new categories of bug.

A sample of the default-mode errors are not just missing annotations — they're the type checker
catching real problems, which is direct evidence for why this debt is worth paying down now rather
than a pure style exercise:

- `core/session.py:89` and `:149` — `-> tuple[Element:int]`: invalid syntax (mypy: *"did you mean to
  use ',' instead of ':'?"*), meant `tuple[Element, int]`.
- `node.py:117,121,127` — `execute()` is declared `-> dict` and its own docstring says *"Returns:
  bool: True when then actions executed, False otherwise"*, but every actual `return` in the method
  returns `True`/`False`. Signature, docstring, and implementation currently disagree with each
  other; the annotation is simply wrong.
- `util.py:merge()` — declared `dict[str, object]` in and out, but the implementation recurses into
  nested dicts/lists and mutates by index (`result[key][i] = ...`, `.append(...)`). `object` blocks
  exactly the operations this function needs to perform on its own recursive calls (13 of the 44
  baseline errors are in this one function) — the annotation doesn't describe what the function
  actually does; it needs `Any`-based value typing (or a recursive type alias), not tightening.
- `scanner.py:load_rules_from_filepaths(*paths: str|list|tuple)` — the declared type promises each
  vararg can independently be a `str`, `list`, or `tuple`, but the body only actually flattens
  nested lists/tuples when `len(paths) == 1`. Call it with more than one argument where one of them
  is a list (e.g. `load_rules_from_filepaths('a', ['b', 'c'])`) and `sys.path.append(path)` /
  `os.listdir(path)` receive a `list` where a `str` is required — mypy flags this
  (`scanner.py:111`); the signature was never true for that call shape.
- `container.py:sum()`/`variance()` — declared `-> Number` / `-> float`, but the backing cache
  attributes (`self._cached_sum = None`, `self._cached_variance = None` in `__init__`) are never
  given their own type, so mypy infers them as `None`-typed and flags every real assignment as
  incompatible. The fix is annotating the attributes (`Number | None`), not the methods.
- `core/graph.py:Graph.add()` — a local `element` is redeclared with an inferred-incompatible type
  on line 49 after already being bound on line 44 in the same function (`no-redef`), and an
  `Element | None` walks into a slot mypy expects to stay `Element` — worth a manual read to confirm
  the traversal's None-handling is actually intentional at that point, not just annotating past it.
- `factset.py` and parts of `core/graph.py` are currently **entirely unchecked by mypy** (its "By
  default the bodies of untyped functions are not checked" note) — meaning today there is zero
  static verification of `Factset.add_facts`/`update_facts`/`del_facts`, the FactSet's core mutation
  logic, from any tool. This isn't hypothetical debt; it's an actual blind spot.

**Also discovered, adjacent to this plan but load-bearing for it:** the repository's only GitHub
Actions workflow lives at `.github/workflow/python-publish.yml` — **singular** `workflow/`. GitHub
Actions only discovers workflows under `.github/workflows/` (plural); a file in the singular
directory never runs, on any trigger. So today there is no CI at all — not lint, not tests, not the
publish workflow itself despite `on: release: types: [published]` looking correctly configured. This
plan's new CI job (Phase 1) goes in the correct plural directory; fixing/relocating the existing
publish workflow is noted but left to the user, see Explicitly out of scope.

## Design

**Scope boundary, decided up front:** this plan types the library's own public API surface (`Service`,
`Repository`, `Ruleset`, `Rule`, `Fact`/`Collection`/`Event`, `Factset`, `controls`, `Collector`,
`scanner`) and its internals (`core/`). It does **not** attempt to type the dynamic `ctx`/`this`
objects that rule authors' `matches`/`then` lambdas receive — `ctx` is a `SimpleNamespace` that
rules populate with arbitrary attributes via `assign(ctx, **kwargs)`, and `this` is whatever fact
type matched. That dynamism is the DSL's actual design (see `docs/rules-authoring.md`), not an
oversight, and making it statically checkable would mean a different DSL (e.g. `TypedDict`/`Protocol`
per rule), which is a redesign, not a typing cleanup. `SimpleNamespace`/`object`-typed `ctx`
parameters on library-side functions that accept a rule-author-supplied context (e.g.
`helper.assign`, already typed this way) are the correct, final typing for this boundary — not a gap
to close later.

**Mypy strictness profile, decided:** not full `--strict`. 314 vs. 44 errors is mostly
`no-untyped-def`/`no-untyped-call` noise cascading from the same handful of root causes, and
`--strict` also turns on checks (e.g. `disallow_any_explicit`-adjacent friction around `**kwargs`
attached via `setattr`) that fight the library's intentionally dynamic kwargs-to-attributes pattern
(`Fact(**kwargs)`, `Rule(**kwargs)`, `Collector(**kwargs)` all do `setattr(self, key, value)` for
arbitrary caller-supplied kwargs — this is public API, not sloppiness, and stays `**kwargs: object`
with `# type: ignore[misc]` only where `setattr` itself needs it, not redesigned). Target profile
instead, added to `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.13"
mypy_path = "src"
warn_redundant_casts = true
warn_unused_ignores = true
warn_unreachable = true
# Ratchet: flips to true globally once Phase 4 finishes; per-module overrides below
# turn it on file-by-file as each is completed, so partial progress stays enforced
# instead of silently regressing.
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = "knowledgenet.helper"
disallow_untyped_defs = true
```
(`no_implicit_optional` is mypy's default since ~0.990 and needs no explicit setting; it's what
flags the `param: str = None` cases below.)

### Phase 1 — Tooling baseline (no source changes)

- Add `mypy` to the `dev` group in `pyproject.toml` (alongside `pytest`, `ruff` is not currently used
  in this repo and is out of scope to introduce here — this plan is about typing, not linting).
- Add the `[tool.mypy]` config above.
- Create `.github/workflows/ci.yml` (correct plural directory) running, on push and PR:
  `python -m pytest -rPX -s` and `python -m mypy src/knowledgenet`. This is also the first time *any*
  workflow in this repo actually executes on GitHub, independent of this typing effort.
- Commit the baseline numbers above as the starting point; every later phase's Verification step
  re-runs `mypy src/knowledgenet` and reports the new count.

### Phase 2 — Fix the real bugs mypy's baseline run surfaced

Not annotation additions — actual defects, fixed regardless of what the rest of this plan does:

- `core/session.py:89,149` — `tuple[Element:int]` → `tuple[Element, int]`.
- `node.py:execute()` — change the declared return type from `-> dict` to `-> bool`, matching both
  the implementation and its own docstring (three-way mismatch resolved in favor of the two that
  already agree).
- `container.py.__init__` — annotate `self._cached_sum: Number | None`, `self._cached_variance:
  float | None`, `self._cached_min`/`self._cached_max` similarly, so `sum()`/`variance()`'s existing
  `-> Number`/`-> float` declarations stop conflicting with their own cache fields.
- `util.py:merge()` — retype to `dict[str, Any]` in/out (recursive JSON-like structure; `Any` is the
  honest type here, not a downgrade — `object` was never checkable for this function's actual
  behavior).
- `scanner.py:load_rules_from_filepaths` — either fix `_find_modules`'s call path to flatten nested
  list/tuple args regardless of `len(paths)` (matching what the signature promises), or narrow the
  signature to what's actually supported and update `docs/rules-authoring.md`/docstring accordingly.
  Decide by checking existing callers/tests first (`test/unit/`, `knowledgenet-examples`) for which
  call shape is actually relied on.
- `core/graph.py:Graph.add()` — resolve the `element` redefinition and the `Element | None` vs.
  `Element` mismatch by reading the traversal logic; likely just needs the loop-local `element` typed
  `Element | None` explicitly (matching `last`), not a behavior change.
- `scanner.py:21` — annotate `registry: dict[str, dict[str, list[Rule]]] = {}`.
- `core/file_trace_exporter.py:_span_to_dict` — annotate the local `d` (currently untyped, inferred
  as a union that then can't be indexed/appended to consistently); give it an explicit
  `dict[str, Any]` since span shapes are genuinely heterogeneous (`getattr` off an untyped OTel SDK
  object).

### Phase 3 — Modernize old-style typing (mechanical, no behavior change)

- `ruleset.py`, `scanner.py`, `core/session.py`: `Union[X, Y]` → `X | Y`.
- `util.py`: `typing.List` → builtin `list[...]`.
- `container.py`, `rule.py`, `ftypes.py`, `core/file_trace_exporter.py`: `typing.Callable` →
  `collections.abc.Callable`, `typing.Sequence` → `collections.abc.Sequence`.
- `core/file_trace_exporter.py:export()` — drop the quotes on `-> "SpanExportResult"`;
  `SpanExportResult` is imported unconditionally at module top already, the quoting serves no
  purpose (not a `TYPE_CHECKING`-guarded import).
- `core/graph.py`'s `from __future__ import annotations` — with a 3.13+ floor this import predates
  PEP 649 (deferred annotation evaluation, standard since 3.14) and is redundant. Lowest priority in
  this phase; drop only after Phase 4 confirms nothing (e.g. `typing.get_type_hints` calls, there are
  none currently) depends on the stringified-annotation behavior it enables.
- Fix the three implicit-Optional signatures mypy flagged: `rule.py:76` and `ftypes.py:80`
  (`of_type: type | str = None, named: str = None` → `type | str | None = None`, `str | None =
  None`), `scanner.py:30` (`id: str = None` → `str | None = None`).

### Phase 4 — Fix mutable default arguments

Not mypy-flagged (mypy doesn't check this), found by inspection — the standard shared-mutable-default
footgun, all four take a `global_ctx`/`include_only` dict-or-list default:

- `service.py:27` `Service.__init__(..., global_ctx={}, ...)`
- `ruleset.py:16` `Ruleset.__init__(..., global_ctx={})`
- `core/session.py:14` `Session.__init__(..., global_ctx={}, ...)`
- `core/perm.py:1` `combinations(ll, include_only=[])`

Change each to `global_ctx: dict[str, object] | None = None` / `include_only: list | None = None`
with `if global_ctx is None: global_ctx = {}` inside. Also worth a quick check whether `global_ctx`
is ever mutated in place downstream (`core/session.py`, `node.py`) — if so this is a live bug
(state leaking between `Service`/`Ruleset`/`Session` instances that didn't pass their own
`global_ctx`), not just a latent one; document the finding either way in this plan's Verification.

### Phase 5 — Annotate the untyped public-API surface

Ratchet `disallow_untyped_defs = true` onto each module's `[[tool.mypy.overrides]]` entry as it's
completed, in this order (highest external-visibility first):

1. `controls.py` — `insert`/`update`/`delete`/`switch`/`next_ruleset`/`end`. Small, and the functions
   rule authors call most directly in `then=` actions.
2. `factset.py` — `add_facts`/`update_facts`/`del_facts`/`find`/`_get_class_hierarchy` and the
   `_type_to_facts`/`_type_collectors`/etc. dict attributes (annotate in `_init_dictionaries`,
   currently untyped and unchecked — see baseline note above).
3. `service.py` — `Service.__init__`/`execute`/`_find_switch`/`_execute_service`. The top-level
   entrypoint (`knowledgenet.service.Service.execute()` per `docs/concepts.md`).
4. `node.py` — `Leaf.__init__`/`execute`, `Node.__init__`/`execute`/`_execute_thens`/
   `reset_whens` (the latter two already partially annotated).
5. `core/session.py`, `core/graph.py` remainder, `core/tracer.py`, `core/perm.py.cartesian`'s `ll`
   param — internals; needed so `Any` doesn't leak back out through `service.py`/`factset.py` once
   those are typed.
6. `decorator.py` — `ruledef`/`ruledef_wrapper`/`wrapper`. Expect friction here specifically:
   `--strict`'s `decorator.py:60` error (`_Wrapped[...] has no attribute "__ruledef__"`) is the
   `functools.wraps`-preserves-dynamic-attribute pattern mypy structurally can't verify; resolve with
   a single targeted `# type: ignore[attr-defined]` at that line with a comment explaining why,
   rather than restructuring the decorator.
7. `scanner.py` remainder (`clear`, `lookup`, `_load_rules_from_module`, `_find_modules`).

Convention for dunders across all of the above (apply once, consistently, rather than re-deciding per
file): `__str__`/`__repr__` return `str`, `__eq__(self, other: object) -> bool`, `__hash__(self) ->
int`.

### Phase 6 — Close the ratchet

Once Phase 5's overrides cover every module, collapse them into a single top-level
`disallow_untyped_defs = true` in `[tool.mypy]` and delete the per-module override blocks. Confirm
`mypy src/knowledgenet` (the agreed profile, not `--strict`) is clean, and that the CI job from
Phase 1 is green on the default branch.

## Explicitly out of scope

- Typing `ctx`/`this` inside rule-author `matches`/`then` lambdas, or redesigning the DSL toward
  `TypedDict`/`Protocol`-based fact contexts — see Design's scope boundary above. `SimpleNamespace`/
  dynamic-attribute typing at that boundary is correct as-is.
- Adopting `--strict` mypy, or any linter (`ruff`, `flake8`, etc.) — this plan is scoped to typing
  only; introducing a linter is a separate decision or plan.
- Relocating/fixing `.github/workflow/python-publish.yml` (singular directory, currently inert) —
  flagged in Context as directly relevant discovered-context, but fixing someone's publish pipeline
  is not part of a typing plan; raised to the user separately.
- Any change to `knowledgenet-examples`/`autoins` — that repo pins `knowledgenet==1.0.0` from
  PyPI/a built wheel; nothing here changes runtime behavior or the public API shape, so no version
  bump or example-repo change is implied. If Phase 2's `scanner.py` vararg-shape question resolves
  toward *narrowing* the signature rather than fixing the implementation, revisit whether
  `knowledgenet-examples` relies on the currently-broken call shape first.
- Sphinx/API-doc regeneration (`docs/api/*.md`) — unaffected by type annotations (Sphinx's
  `autodoc`/markdown builder here isn't configured to render type hints into prose); no need to
  rebuild docs as part of this plan unless that's separately requested.
- Runtime type validation/enforcement (e.g. `pydantic`, `typeguard`) — this plan is static typing
  only; facts remain plain Python objects with no runtime schema checking, unchanged.

## Verification

1. After Phase 1: `python -m mypy src/knowledgenet` runs (config picked up from `pyproject.toml`,
   default profile) and reproduces the 44-error baseline exactly — confirms the config itself
   introduces no behavior change before any source edits. Push a throwaway commit to confirm
   `.github/workflows/ci.yml` actually triggers on GitHub (closing the loop on the discovered
   singular-directory issue for at least this new workflow).
2. After each of Phases 2-4: `python -m mypy src/knowledgenet`, confirm the error count has dropped
   by exactly the errors that phase targeted and nothing new appeared. `python -m pytest -rPX -vv -s`
   full suite green after every phase — these are behavior-affecting changes (implicit-Optional
   fixes, mutable-default fixes, the `node.py`/`scanner.py`/`graph.py` bug fixes), not pure
   annotation work, so test coverage is the real safety net there.
3. After Phase 4's mutable-default fix: if the `global_ctx`-is-mutated-downstream check finds a real
   issue, write a regression test demonstrating state was (before) or is no longer (after) leaking
   between two `Service`/`Ruleset` instances constructed without an explicit `global_ctx`.
4. After each module in Phase 5: `python -m mypy src/knowledgenet` with that module's
   `disallow_untyped_defs = true` override active, confirm it's clean before moving to the next
   module (ratchet never regresses).
5. After Phase 6: `python -m mypy src/knowledgenet` clean with a single top-level
   `disallow_untyped_defs = true` and no per-module overrides; full `pytest` suite green;
   `python -m build` still succeeds (confirms packaging/`pyproject.toml` changes didn't break the
   distribution).
6. Spot-check that IDE-visible value actually materializes: open `service.py`'s `execute()` and
   `factset.py`'s `find()` in an editor with mypy/pylance-style hover support and confirm parameter
   and return types now show real types, not `Any`/nothing — the concrete symptom from the original
   complaint ("lacks typed interface").
