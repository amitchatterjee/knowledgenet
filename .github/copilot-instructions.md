# Copilot Instructions for Knowledgenet

Project overview
- Knowledgenet is a RETE-based rules engine implemented as a Python library. It evaluates `facts` against authored `rules` organized into `rulesets` and `repositories` and exposes a service entrypoint via `knowledgenet.service.Service.execute()` to process transactions and return result facts.
- Core modules: `rule`, `ruleset`, `repository`, `service`, `factset`, `scanner`, `graph`/`node`, `container`, and `decorator` (see `src/knowledgenet/`).
- Intended usage: integrate the library into an application, initialize a `Service` with a repository of rulesets, then invoke `execute(input_facts)` per transaction. See `doc/concepts.md` and `doc/rules-authoring.md` for conceptual and authoring guidance.

Purpose
- Provide concise, actionable guidance for AI assistants (Copilot) and contributors working on the Knowledgenet Python project.

How to use this file
- Read before making edits that affect project structure, APIs, tests, or packaging.
- Follow local contributor and testing workflows below.

Repository layout (high level)
- Source: `src/knowledgenet/`
- Tests: `test/unit/` and top-level `test/`

Development workflow (recommended)
- Create a feature branch for non-trivial work.
- Use the `apply_patch` tool for file edits when automating changes.
- Keep changes minimal and focused; do not reformat unrelated files.

Editing guidelines for Copilot-generated patches
- Prefer surgical changes: modify the fewest files and lines necessary.
- Preserve existing code style and public APIs unless the change explicitly requires a refactor.
- Do not add or change licenses or headers.
- When adding or editing code, also add/adjust unit tests under `test/unit/`.

Testing locally
- Use a virtual environment with the project's Python version.
- Install dev requirements if needed; the repository uses `pyproject.toml` for packaging.
- Run tests with:

```bash
python -m pytest -q
```

Formatting & linting
- Keep to the project's existing style. If formatting tools are added, run them only on changed files.

Commit messages and PRs
- Keep commit messages focused and descriptive (one line summary + optional body).
- In PR descriptions, list the files changed and the motivation.

When to ask the maintainers
- For breaking API changes, major refactors, CI changes, or dependency upgrades, request a review from core maintainers listed in the repo.

Notes for Copilot agents
- Use the `manage_todo_list` tool to create/track multi-step plans before editing.
- Provide short preambles before running file-modifying tools (what you're about to do and why).
- After edits, run tests where possible and give a concise progress update.
- If a generated change introduces errors, attempt to fix them (up to 3 iterations) and then ask for guidance if unresolved.

