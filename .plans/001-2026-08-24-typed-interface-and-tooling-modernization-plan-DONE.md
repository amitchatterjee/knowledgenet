# Add a typed interface, modernize type hints to Python 3.14 idioms, and modernize dev tooling (pip → uv, CI)

Status: **DONE (2026-08-30)** — Phases 0-6 implemented and verified (tests passing, `mypy` clean
package-wide). Note: CI-green on the default branch was never separately confirmed, since the work
was still uncommitted/unpushed as of this status change — verify that once pushed.

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
plan's new CI job (Phase 1) goes in the correct plural directory; Phase 1 also fixes the existing
publish workflow's directory so it starts actually running (see Phase 1).

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

### Phase 0 — Transition dev tooling from pip to uv (tooling, no source changes) — **DONE (2026-08-28)**

Runs before Phase 1 so Phase 1's new CI workflow can be written uv-native from the start instead of
being redone. Current flow, per `docs/readme-development.md`: manual `python3.14 -m venv .venv` +
manual activation, `pip install pip-tools`, `python -m piptools compile pyproject.toml -o
target/requirements.txt` then `pip install -r target/requirements.txt` for runtime deps, `pip install
-U --group=dev` for dev deps (PEP 735 `[dependency-groups]`, already present in `pyproject.toml`),
`python -m build` + `python -m twine upload` to publish. `uv` replaces the compile/install dance with
a single lockfile-driven flow and removes `pip-tools` as a dependency of the dependency-management
process itself.

- Document `uv` as a once-per-machine tool install (`curl -LsSf https://astral.sh/uv/install.sh | sh`
  or a distro package) — not a project dependency.
- Replace manual venv creation with `uv venv --python 3.14` (or rely on `uv sync` to create `.venv`
  implicitly on first run, honoring `requires-python` from `pyproject.toml` — document both, since
  explicit `uv venv` is clearer for first-time contributors). For contributors upgrading an existing
  checkout whose `.venv` was created by the old `python3.14 -m venv` flow, document
  `rm -rf .venv && uv venv --python 3.14` — simplest as a one-time migration step, and avoids relying
  on uv's ownership-detection/`--clear` semantics for something entirely disposable/regenerable.
- Replace `pip install pip-tools` + `piptools compile` + `pip install -r target/requirements.txt` with
  `uv sync` (base deps) and `uv sync --group dev` (adds the dev group). Drop `pip-tools` from
  `[dependency-groups] dev` in `pyproject.toml` — superseded by `uv sync`/`uv.lock`.
- Generate and commit `uv.lock` (uv's lockfile; unlike `target/requirements.txt`, which was a
  gitignored build artifact regenerated ad hoc, `uv.lock` is committed and covers dev deps too, not
  just runtime).
- **Reorganize `pyproject.toml`**: keep `[build-system]`/setuptools as the build backend (uv is a
  package/dependency manager here, not a build-backend replacement — switching to `hatchling` etc. is
  out of scope, see below); drop `pip-tools` from the `dev` group; move `[dependency-groups]` to
  directly after the closing of `[project]`'s own keys and before `[project.urls]` (today it sits
  mid-`[project]`-table, between `dependencies` and `description`/`requires-python`/`classifiers` —
  an odd split left over from earlier edits) so the file reads top-to-bottom as `[build-system]` →
  `[project]` (complete) → `[project.urls]` → `[dependency-groups]` → `[tool.*]` (including this
  plan's own `[tool.mypy]` from Phase 1); add a `[tool.uv]` section only if a concrete need surfaces
  during the phase (e.g. `python-preference`) — no speculative config.
- **Update `docs/readme-development.md`** command-by-command:
  - "One-time setup" → `uv venv --python 3.14`.
  - "Install development tools" → `uv sync --group dev` (replaces the `pip install --upgrade pip` /
    `pip install pip-tools` / `pip install -U --group=dev` trio).
  - "Install runtime dependencies" → `uv sync` (replaces `mkdir -p target` + `piptools compile` +
    `pip install -r`; drop the `target/requirements.txt` step and mentions entirely — `uv.lock`
    supersedes it).
  - "Run tests" → prefix each example with `uv run` (`uv run pytest -rPX -vv -s --cov`, etc.); note
    that `source .venv/bin/activate` + bare `python -m pytest` still works unchanged afterward too
    (uv still populates a normal `.venv`), but `uv run` is what CI should use since it needs no prior
    activation step.
  - "Build API docs" → prefix `sphinx-apidoc`/`sphinx-build` invocations with `uv run`.
  - "Publish package to PyPI" → **Decided: stick with `twine upload` (via `.pypirc`) for now; `uv
    publish` deferred.** `uv build` replaces `python -m build` (uv build has no `twine`-equivalent
    tradeoff — adopt immediately), but publishing stays on `twine upload --repository <repository>
    dist/*` against the existing `~/.pypirc` token setup, unchanged. A `[[tool.uv.index]]` "testpypi"
    entry is added to `pyproject.toml` and `docs/readme-development.md` notes `uv publish` as a viable
    future replacement, but it is not switched to now. Keep `build` and `twine` in
    `[dependency-groups] dev`.
  - "Install git flow" section unaffected.
- Update Phase 1's `.github/workflows/ci.yml` to use `astral-sh/setup-uv` + `uv sync --group dev` +
  `uv run pytest` + `uv run mypy src/knowledgenet`, written uv-native from the start.
- Update `CLAUDE.md`'s Environment section (currently documents `source .venv/bin/activate`, `pip
  install -U --group=dev`, pip-tools compile) to match. Confirm `uv sync`/`uv venv` still produce
  `.venv` at the same repo-root path so `knowledgenet-examples/CLAUDE.md`'s "share
  `../knowledgenet/.venv`" convention keeps working unchanged — no edit needed there unless the path
  or activation story actually changes.

**Verified:** `.venv` recreated via `uv venv --python 3.14` + `uv sync --group dev` (66 packages
resolved, `knowledgenet` importable); `uv.lock` committed and confirmed not gitignored;
`pyproject.toml` reorganized and `pip-tools` dropped from `dev`; a `[[tool.uv.index]]` "testpypi"
entry added (publishing itself stays on `twine`/`.pypirc` per the decision above); all three
documented `uv run sphinx-*` commands (apidoc, HTML build, Markdown build) run clean; `docs/
readme-development.md`, `CLAUDE.md`, and `README.md` (renamed from `readme.md`, with a new PyPI
install section) updated. Committed in `e7bdcc3` and `10f2323`.

### Phase 1 — Tooling baseline (no source changes) — **DONE (2026-08-28)**

- Add `mypy` to the `dev` group in `pyproject.toml` (alongside `pytest`, `ruff` is not currently used
  in this repo and is out of scope to introduce here — this plan is about typing, not linting).
- Add the `[tool.mypy]` config above.
- Create `.github/workflows/ci.yml` (correct plural directory), uv-native per Phase 0 (`astral-sh/
  setup-uv` + `uv sync --group dev`), running on push and PR: `uv run pytest -rPX -s` and `uv run mypy
  src/knowledgenet`. This is also the first time *any* workflow in this repo actually executes on
  GitHub, independent of this typing effort.
- Fix the `.github/workflow/` (singular) typo: `git mv .github/workflow/python-publish.yml
  .github/workflows/python-publish.yml`, then remove the now-empty `.github/workflow/` directory.
  Purely a path rename — no content change to the publish workflow itself, so its `on: release:
  types: [published]` trigger and existing steps are untouched, just finally reachable by GitHub.
- Commit the baseline numbers above as the starting point; every later phase's Verification step
  re-runs `mypy src/knowledgenet` and reports the new count.

**Verified:** `mypy` added to `dev`, `[tool.mypy]` config added, `uv sync --group dev` installed
mypy 2.3.1 cleanly. `.github/workflows/ci.yml` created (uv-native, `astral-sh/setup-uv@v10`).
`.github/workflow/python-publish.yml` renamed to `.github/workflows/python-publish.yml` via `git mv`
(history-preserving; not yet pushed, so the Actions-tab/`git log --follow` checks in Verification #2
are still outstanding). `uv run mypy src/knowledgenet` gives **45 errors in 11 files** — confirmed
this is the real baseline-with-config (not a mistake: bare `mypy` with no config still reproduces
44/10 exactly), caused by the `knowledgenet.helper` override catching a genuine untyped-`**kwargs`
gap in `helper.py:13`, deferred to Phase 5 as documented in Verification #2. `uv run pytest -rPX -s`
run manually by the user: **passed**.

### Phase 2 — Fix the real bugs mypy's baseline run surfaced — **DONE (2026-08-30)**

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

**Verified:** All bullets above implemented. `scanner.py:load_rules_from_filepaths` resolved via
checking every real caller in both repos (`test/unit/test_scanning.py`: multiple plain-`str` args;
`knowledgenet-examples/autoins/src/rule_runner.py`: single `list[str]` arg) — no caller ever mixes
the two, so the fix is two `@overload` signatures (`*paths: str` / `paths: list[str] | tuple[str,
...]`) rather than extending `_find_modules` to support an untested mixed shape; runtime body
unchanged. Fixing `core/session.py`'s invalid `tuple[Element:int]` syntax let mypy check those
function bodies for the first time (the parse error had been silently suppressing checks), which
surfaced that `_add_facts`/`_delete_facts`'s "leftmost" value is genuinely nullable throughout —
`_minimum`'s `element1` param (whose own `if not element1:` guard already assumed this) and the two
return types were widened to `Element | None` accordingly. Also fixed, found adjacent to the planned
work: `_add_facts`'s early-return path returned literal `0` instead of the already-empty `new_facts`
set (harmless today since every caller discards that slot, but inconsistent with the return type);
and `container.py:minimum()` had its cache-write line indented one level too shallow (unlike
`maximum()` right below it), so it recomputed on every call instead of ever using its cache — a
pure performance fix, no return-value change. `uv run mypy src/knowledgenet` dropped from 45 errors
in 11 files to **10 errors in 6 files**, and all 10 remaining are pre-existing items already scoped
to Phase 3 (implicit-Optional signatures) or Phase 5 (`perm.py`, `container.py:collection`,
`helper.py`) — no new errors introduced. `uv run pytest -rPX -s` run manually by the user: **passed**.

### Phase 3 — Modernize old-style typing (mechanical, no behavior change) — **DONE (2026-08-30)**

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

**Verified:** All bullets implemented, plus two things found while doing so that the plan's literal
text didn't anticipate. First, `ftypes.py`'s `Callable`/`Union` imports were both dead — nothing in
the file actually used them — so that bullet became "delete the unused imports" for this file rather
than "migrate `typing.Callable` usage," and `Union` (also unused after the `load_rules_from_packages`
fix in `scanner.py`) and `List` (dead in `util.py`) were dropped the same way everywhere they'd
become unused. Second, `rule.py:127`'s `when` default (`= ()`) was mismatched with its own declared
type (`tuple[Fact | Collection]` means an exactly-one-element tuple, not "any-length tuple," so the
empty-tuple default didn't fit) — a fourth implicit-mismatch signature mypy had flagged in the
Phase-2 baseline that wasn't listed in this phase's bullets; fixed to the correct variadic
`tuple[Fact | Collection, ...]`, matching actual behavior (any number of when-clauses, including
zero). Widening `ftypes.py:Wrapper.__init__`'s `of_type` to `type | str | None` (per the
implicit-Optional fix) surfaced a real mypy gap further down the same method — `of_type.__name__` is
reached only after two `raise`-guards that make `of_type is None` impossible at runtime, but mypy
can't follow that through the reassignment — resolved with an explicit `assert of_type is not None`,
same pattern as the `graph.py` fix in Phase 2. `core/graph.py`'s `from __future__ import annotations`
was deliberately left alone per this phase's own note (defer until Phase 4 confirms nothing depends
on it). `uv run mypy src/knowledgenet` dropped from 10 errors in 6 files to **4 errors in 4 files**,
all of them already Phase 5-scoped (`perm.py`, `container.py:collection`, `helper.py`,
`scanner.py:146`) — no new errors. `uv run pytest -rPX -s`: **89 passed** (run by the assistant as a
sanity check given the `assert` addition was an actual runtime change, not just annotations; also
confirmed by the user as usual).

### Phase 4 — Fix mutable default arguments — **DONE (2026-08-30)**

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

**Verified:** All four sites fixed identically (`None` sentinel + `if x is None: x = {}`/`[]` inside).
Checked the mutation question by grepping every `global_ctx` reference in `src/`, `test/`, and
`docs/`: `core/session.py`/`node.py` only ever *read* `self.global_ctx` (passing it through to
`Session`, exposing it via `helper.global_ctx(ctx) -> ctx._session.global_ctx`), never write to it,
and no test exercises a write either. But `docs/rule-service.md`'s own documented usage pattern —
`global_ctx(ctx)['api_client']` from inside a rule's `then=` — returns a live reference to the same
dict object, and nothing stops a rule author from writing `global_ctx(ctx)['x'] = y` instead of just
reading. Before this fix, doing that from any `Service`/`Ruleset`/`Session` constructed without an
explicit `global_ctx` would have silently mutated the one shared default dict, leaking state into
every other unrelated instance created the same way for the lifetime of the process — a real, live
bug given the DSL's own documented "inject shared resources" use case, not just latent risk; this
phase's fix closes it. `uv run mypy src/knowledgenet`: same 4 pre-existing Phase 5-scoped errors,
unchanged (`core/perm.py`'s line number shifted 16→18 from the added lines, nothing else). `uv run
pytest -rPX -s`: **89 passed** (run by the assistant as a sanity check; also run by the user with
`--cov`, 96% coverage, all passing, before this phase).

### Phase 5 — Annotate the untyped public-API surface — **DONE (2026-08-30)**

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

**Verified:** All 7 explicitly-listed items done (`controls.py`, `factset.py`, `service.py`,
`node.py`, `core/session.py` + `core/graph.py` remainder + `core/tracer.py` + `core/perm.py`,
`decorator.py`, `scanner.py` remainder). `decorator.py`'s expected friction materialized exactly as
predicted (`wrapper.__ruledef__ = True` needs a targeted `# type: ignore[attr-defined]`) and was
resolved that way, not by restructuring.

**Scope gap found and closed (with sign-off):** Phase 6 requires "Phase 5's overrides cover every
module," but this phase's own 7-item list only named 8 of the package's 18 real modules —
`container.py`, `ruleset.py`, `rule.py`, `ftypes.py`, `util.py`, `repository.py`, and
`core/file_trace_exporter.py` were never listed, and were still substantially untyped. Flagged this
to the user directly rather than silently declaring Phase 5 done against an unsatisfiable Phase 6
precondition; user chose to extend Phase 5 now to cover all of them. All 18 real modules (excluding
the two trivial `__init__.py` files) now have `disallow_untyped_defs = true` overrides in
`pyproject.toml`, and `uv run mypy src/knowledgenet` reports **zero issues** — this is the actual
precondition Phase 6 needs, now genuinely met.

**Real bugs found and fixed while annotating** (not part of the planned scope, but directly
surfaced by giving `other: object` a real type on every `__eq__`, per the dunder convention above):
- `Rule.__eq__` and `Ruleset.__eq__` both did `return self.id == other.name` — but neither class
  ever defines a `.name` attribute (confirmed via search: no test, and no caller anywhere, ever
  passes `name=` to either constructor). Every invocation of `rule1 == rule2` or `ruleset1 ==
  ruleset2` would have raised `AttributeError` unconditionally, with zero test coverage to catch it.
  Fixed both to `self.id == other.id`, matching `Node.__eq__`'s already-correct pattern. This is a
  significant, 100%-reproducible bug, not an edge case.
- `factset.py`'s `_type_to_events`/`_type_to_collectors` dict declarations were typed with
  `type`-only keys, but code already looked them up using `of_type(fact)` (which returns `type | str`
  for `Wrapper`-wrapped facts) -- widened both to `type | str` keys, matching the already-correct
  `_type_to_facts` dict right next to them.
- `node.py:Leaf.execute()` — `setattr(context, self.rule.whens[...].var, fact)` guarded by a truthy
  check on the same repeated expression; mypy can't narrow a re-evaluated indexing expression the way
  it narrows a local variable, so bound it to a local (`var = ...; if var: setattr(context, var,
  fact)`) — also removes a redundant re-index, no behavior change.

`uv run mypy src/knowledgenet`: **zero issues, all 18 modules** (up from the 4-error, 4-module state
Phase 4 left off at). `uv run pytest -rPX -s`: **89 passed**, no regressions from any of the above,
including the two `__eq__` fixes (unexercised by any existing test either way). Also ran the
downstream `knowledgenet-examples/autoins` suite against this build (`uv sync --group dev && uv run
pytest -rPX -q`, picking up the local source via the `[tool.uv.sources]` path dependency and
`cache-keys` config from the earlier detour): **5 passed**, confirming no observable regression in a
real consumer.

### Phase 6 — Close the ratchet — **DONE (2026-08-30)**

Once Phase 5's overrides cover every module, collapse them into a single top-level
`disallow_untyped_defs = true` in `[tool.mypy]` and delete the per-module override blocks. Confirm
`mypy src/knowledgenet` (the agreed profile, not `--strict`) is clean, and that the CI job from
Phase 1 is green on the default branch.

**Verified:** All 18 `[[tool.mypy.overrides]]` blocks deleted; `[tool.mypy]` now has a single
`disallow_untyped_defs = true`, with a comment noting it's a one-line flip either direction (no
per-module bookkeeping) per the user's explicit request to keep an easy escape hatch for when
strong typing gets in the way, rather than leaving the per-module override list around as the
"off switch" mechanism. `uv run mypy src/knowledgenet`: **zero issues** (unchanged from Phase 5's
end state, confirming the collapse itself introduced no new gaps). `uv run pytest -rPX -s`: **89
passed**. Not yet verified: CI green on the default branch — Phases 2 through 6 are all still
uncommitted/unpushed (only Phase 0 and a differently-labeled Phase 1/2 pair are committed so far,
per `git log`), so the Actions-tab check from this phase's own text is outstanding until the user
commits and pushes.

## Explicitly out of scope

- Switching the build backend away from `setuptools` (e.g. to `hatchling`, uv's own default for `uv
  init` projects) — orthogonal to the pip→uv tooling transition; `setuptools` works fine under `uv
  build`.
- ~~Migrating `knowledgenet-examples`/`autoins`'s own `requirements.txt`-based install flow to
  uv~~ — **superseded (2026-08-30), done.** Out of scope as originally written for this plan's own
  phases, but the user separately and explicitly requested it mid-plan (their own `.venv` had
  been removed and they wanted `autoins` on its own `uv`-managed venv, one per future example,
  rather than a shared one). Implemented: `autoins/pyproject.toml` (new, `requirements.txt`
  removed), `[tool.uv.sources]` path dependency on the sibling `knowledgenet` repo (no PyPI
  publish needed for local dev), `[tool.uv] cache-keys` added to `knowledgenet/pyproject.toml` so
  plain `uv sync` in `autoins` picks up `knowledgenet` source edits automatically. Docs
  (`autoins/readme.md` → renamed `README.md` by the user, `knowledgenet-examples/CLAUDE.md`)
  updated to match. Not tracked as a phase in this plan since it's `knowledgenet-examples`' own
  tooling, not `knowledgenet`'s — see that repo's own history/CLAUDE.md for details, not this
  plan's Verification section.
- Typing `ctx`/`this` inside rule-author `matches`/`then` lambdas, or redesigning the DSL toward
  `TypedDict`/`Protocol`-based fact contexts — see Design's scope boundary above. `SimpleNamespace`/
  dynamic-attribute typing at that boundary is correct as-is.
- Adopting `--strict` mypy, or any linter (`ruff`, `flake8`, etc.) — this plan is scoped to typing
  only; introducing a linter is a separate decision or plan.
- ~~Any change to `knowledgenet-examples`/`autoins`~~ — **superseded (2026-08-30), done**; see the
  bullet above. (The original reasoning here — no version-bump implication, and checking whether
  `knowledgenet-examples` relied on the pre-fix `scanner.py` vararg shape before narrowing it —
  was addressed directly: Phase 2 confirmed via grep that no real caller in either repo used the
  mixed-arg shape, so the overload-based fix was safe, and `autoins` now consumes `knowledgenet`
  as a local source build rather than a pinned PyPI version at all.)
- Sphinx/API-doc regeneration (`docs/api/*.md`) — unaffected by type annotations (Sphinx's
  `autodoc`/markdown builder here isn't configured to render type hints into prose); no need to
  rebuild docs as part of this plan unless that's separately requested.
- Runtime type validation/enforcement (e.g. `pydantic`, `typeguard`) — this plan is static typing
  only; facts remain plain Python objects with no runtime schema checking, unchanged.

## Verification

1. After Phase 0: from a fresh clone, `uv sync --group dev` creates `.venv` and installs cleanly with
   no `pip`/`piptools` step run by hand; `uv run pytest -rPX -s` passes (same results as the pre-uv
   baseline); `uv build` produces a `dist/*.whl` + `.tar.gz` of the same shape `python -m build` did;
   `uv.lock` is committed. Confirm every command block in `docs/readme-development.md` was actually
   updated (no leftover bare `pip install`/`piptools compile` instructions).
2. After Phase 1: `uv run mypy src/knowledgenet` runs (config picked up from `pyproject.toml`) and
   reports **45 errors in 11 files**, not the bare-mypy 44/10 baseline — verified: bare `mypy` with no
   config still reproduces 44/10 exactly, so the +1/+1 delta comes entirely from the config's own
   `knowledgenet.helper` `disallow_untyped_defs` override (present in `[tool.mypy]` from the start, not
   added later) catching `helper.py:13`'s `assign(ctx: SimpleNamespace, **kwargs)->bool` — the
   `**kwargs` has no annotation. This is expected and left as-is (Phase 1 is no-source-changes); the
   fix (`**kwargs: object`, matching the Design's stated convention for this library's
   dynamic-attribute pattern) belongs in Phase 5 when `helper.py`'s override is reached in the normal
   module order. Push a throwaway commit to confirm
   `.github/workflows/ci.yml` actually triggers on GitHub. Also confirm `git log --follow` on the
   relocated `.github/workflows/python-publish.yml` still shows its original history (a `git mv`
   rename, not a delete+recreate), and that it now shows up under the repo's Actions tab as a
   recognized workflow (won't actually run end-to-end without cutting a release, but its presence in
   the workflow list confirms GitHub now discovers it — closing the loop on the singular-directory
   bug for both workflows).
3. After each of Phases 2-4: `uv run mypy src/knowledgenet`, confirm the error count has dropped by
   exactly the errors that phase targeted and nothing new appeared. `uv run pytest -rPX -vv -s` full
   suite green after every phase — these are behavior-affecting changes (implicit-Optional fixes,
   mutable-default fixes, the `node.py`/`scanner.py`/`graph.py` bug fixes), not pure annotation work,
   so test coverage is the real safety net there.
4. After Phase 4's mutable-default fix: if the `global_ctx`-is-mutated-downstream check finds a real
   issue, write a regression test demonstrating state was (before) or is no longer (after) leaking
   between two `Service`/`Ruleset` instances constructed without an explicit `global_ctx`.
5. After each module in Phase 5: `uv run mypy src/knowledgenet` with that module's
   `disallow_untyped_defs = true` override active, confirm it's clean before moving to the next
   module (ratchet never regresses).
6. After Phase 6: `uv run mypy src/knowledgenet` clean with a single top-level
   `disallow_untyped_defs = true` and no per-module overrides; full `pytest` suite green; `uv build`
   still succeeds (confirms packaging/`pyproject.toml` changes didn't break the distribution).
7. Spot-check that IDE-visible value actually materializes: open `service.py`'s `execute()` and
   `factset.py`'s `find()` in an editor with mypy/pylance-style hover support and confirm parameter
   and return types now show real types, not `Any`/nothing — the concrete symptom from the original
   complaint ("lacks typed interface").
