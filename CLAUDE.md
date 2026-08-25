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
- Virtualenv lives at `.venv` in this repo root: `source .venv/bin/activate`. This same venv is also used for `knowledgenet-examples` work — there is no separate venv per project.
- Dev tools: `pip install -U --group=dev` (pytest, pytest-cov, build, debugpy, twine, pip-tools, sphinx, sphinx-markdown-builder).
- Runtime deps are compiled with pip-tools: `python -m piptools compile pyproject.toml -o target/requirements.txt && pip install -r target/requirements.txt`.

## Testing

Run from the repo root (pytest.ini sets `pythonpath = src test/unit`):

```bash
python -m pytest -rPX -vv -s --cov        # with coverage
python -m pytest -rPX -vv -s              # without coverage
python -m pytest -rPX -vv -s --log-cli-level=DEBUG
python -m pytest -rPX -vv -s 'test/unit/test_basic.py::test_one_rule_single_when_then'  # single test
```

When adding or changing behavior in `src/knowledgenet/`, add or update the corresponding test under `test/unit/`.

## Building API docs

Only needed when publishing docs, but keep in mind that `docs/api/*.md` is generated, not hand-edited:

```bash
sphinx-apidoc -f -e -o target/sphinx/apidoc src/knowledgenet src/knowledgenet/core
sphinx-build -c src/api -D master_doc=modules -b markdown -d target/sphinx/doctrees-markdown target/sphinx/apidoc target/sphinx/markdown
cp -a target/sphinx/markdown/. docs/api/
```

## Editing conventions

- Prefer surgical changes: touch the fewest files/lines necessary; don't reformat unrelated code.
- Preserve existing public APIs (`src/knowledgenet/*.py`, excluding `core/`) unless the task explicitly calls for a breaking change — this is a published PyPI package (`knowledgenet`).
- `src/knowledgenet/core/` is internal; changes there are lower-risk for API compatibility but still need test coverage.
- Don't change license headers.
- This project uses git flow (`develop` is the integration branch; releases/features branch off it).
