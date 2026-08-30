# Knowledgenet

A Python RETE rules engine library (an adaptation of Charles Forgy's RETE algorithm). Applications supply **facts** and **rules**; the engine pattern-matches facts against rules organized into **rulesets** and **repositories**, and exposes a transaction entrypoint via `knowledgenet.service.Service.execute()`.

Read `docs/concepts.md` before making non-trivial changes — it defines the core vocabulary (Service, Facts, FactSet, Rule, Ruleset, Repository, Node, Leaf, Graph, Session) that the code and this file assume you know.

## Repository layout

- `src/knowledgenet/` — the library. Key modules: `rule.py`, `ruleset.py`, `repository.py`, `service.py`, `factset.py`, `scanner.py`, `container.py`, `decorator.py`, `node.py`, `helper.py`, `controls.py`, `ftypes.py`, `util.py`.
- `src/knowledgenet/core/` — internals (`graph.py`, `session.py`, `tracer.py`, `file_trace_exporter.py`, `perm.py`). Treat as private implementation detail, not public API.
- `src/api/` — Sphinx config used to build API docs.
- `test/unit/` — unit tests, plus `test_helpers/` and `scanner-rules/` fixtures.
- `docs/` — `concepts.md` (theory), `rule-service.md` (platform-engineer guide: bootstrapping, fact model design), `rules-authoring.md` (rule-author guide: rule syntax, `@ruledef`, actions), `rule-creation.md`, `docs/api/` (generated API reference, see below).
- `docs/readme-development.md` — full contributor setup/build/publish instructions; this file summarizes the parts needed for day-to-day edits.

## Companion project

`knowledgenet-examples` (sibling repo, typically at `../knowledgenet-examples`) is a reference implementation showing how to use this library — see its own `CLAUDE.md`. When changing public APIs here, check whether the example rules/docs there need updating too.

## Environment

- Python 3.13+ (3.14 recommended).
- Managed with [uv](https://docs.astral.sh/uv/) (install once per machine: `curl -LsSf https://astral.sh/uv/install.sh | sh`, or `pip install --user uv`).
- Virtualenv lives at `.venv` in this repo root, created/managed by uv: `uv venv --python 3.14`. `knowledgenet-examples` (e.g. `autoins`) has moved to its own per-example venv and no longer shares this one — see that repo's own CLAUDE.md.
- Dev tools + runtime deps: `uv sync --group dev` (pytest, pytest-cov, build, debugpy, twine, sphinx, sphinx-markdown-builder, mypy, plus base runtime deps). `uv sync` alone installs just the runtime deps.
- Run commands via `uv run <cmd>` (e.g. `uv run pytest ...`), or `source .venv/bin/activate` and run bare commands as before.

## Testing

Run from the repo root (pytest.ini sets `pythonpath = src test/unit`):

```bash
uv run pytest -rPX -vv -s --cov        # with coverage
uv run pytest -rPX -vv -s              # without coverage
uv run pytest -rPX -vv -s --log-cli-level=DEBUG
uv run pytest -rPX -vv -s 'test/unit/test_basic.py::test_one_rule_single_when_then'  # single test
```

When adding or changing behavior in `src/knowledgenet/`, add or update the corresponding test under `test/unit/`.

## Type checking

```bash
uv run mypy src/knowledgenet
```

Every module has a full typed interface (`disallow_untyped_defs = true` in `pyproject.toml`'s
`[tool.mypy]`, enforced package-wide, not per-module). New/changed code in `src/knowledgenet/` must
stay fully annotated — `uv run mypy src/knowledgenet` should report zero issues before considering
work done. CI runs the same command on every push.

## Building API docs

Only needed when publishing docs, but keep in mind that `docs/api/*.md` is generated, not hand-edited:

```bash
uv run sphinx-apidoc -f -e -o target/sphinx/apidoc src/knowledgenet src/knowledgenet/core
uv run sphinx-build -c src/api -D master_doc=modules -b markdown -d target/sphinx/doctrees-markdown target/sphinx/apidoc target/sphinx/markdown
cp -a target/sphinx/markdown/. docs/api/
```

## Editing conventions

- Prefer surgical changes: touch the fewest files/lines necessary; don't reformat unrelated code.
- Preserve existing public APIs (`src/knowledgenet/*.py`, excluding `core/`) unless the task explicitly calls for a breaking change — this is a published PyPI package (`knowledgenet`).
- `src/knowledgenet/core/` is internal; changes there are lower-risk for API compatibility but still need test coverage.
- Don't change license headers.
- This project uses git flow (`develop` is the integration branch; releases/features branch off it).
