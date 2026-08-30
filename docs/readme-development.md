# For Developers
This page is meant for contributors of this project.


> **Note:** For all the commands below, you must `cd` to the project home directory.  

## One-time setup
This project needs python 3.14 or higher installed. It may work with other versions as well.  

### Install uv:
This project uses [uv](https://docs.astral.sh/uv/) to manage the virtual environment and dependencies. Install it once per machine, either:
```bash
# Standalone installer (no Python dependency; supports `uv self update`)
curl -LsSf https://astral.sh/uv/install.sh | sh
```
or:
```bash
# Via pip, if you'd rather not run the installer script (upgrade with `pip install --upgrade uv`)
pip install --user uv
```

### Create a virtual environment:
```bash
uv venv --python 3.14
```
If you have an existing `.venv` from the old pip-based setup, remove it first: `rm -rf .venv && uv venv --python 3.14`.

### Switch to knowledgenet virtual environment:
```bash
source .venv/bin/activate  
```
You can add the above to $HOME/.bashrc to automatically activate the venv when entering the project directory. This is optional if you use `uv run`/`uv sync` below, which work against `.venv` without requiring activation.

## Install development tools:

```bash
uv sync --group dev
```
This installs the base runtime dependencies plus dev tools (pytest, pytest-cov, build, debugpy, twine, sphinx, sphinx-markdown-builder, mypy) into `.venv`, and creates/updates `uv.lock`.

## Install runtime dependencies:
Only needed if you want the base runtime dependencies without the dev tools above (e.g. to run the library without testing/building it):
```bash
uv sync
```

## Configure the publishing environment:
1. Create an account in [TestPyPI](https://test.pypi.org/account/register/) and [PyPI](https://pypi.org/account/register/).
1. Create an API token in [TestPyPI](https://test.pypi.org/manage/account/#api-tokens) and [PyPI](https://pypi.org/manage/account/#api-tokens).
1. Create a file called `$HOME/.pypirc` with the following content - change the passwords to the tokens you created in step 2.:
```ini
[testpypi]
  username = __token__
  password = pypi-<your_testpypi_token>
[pypi]
  username = __token__
  password = pypi-<your_pypi_token>
```

## Run tests - adjust as needed:

```bash
# With code coverage:  
uv run pytest -rPX -vv -s --cov  
# Without code coverage:  
uv run pytest -rPX -s -vv 
# With debug logging
uv run pytest -rPX -vv -s --log-cli-level=DEBUG  
# Run all tests on a pytest file:  
uv run pytest -rPX -vv -s 'test/unit/test_basic.py'  
# Run a single test:  
uv run pytest -rPX -vv -s 'test/unit/test_basic.py::test_one_rule_single_when_then'  
# Run tests with remote debugging:  
uv run debugpy --listen 0.0.0.0:5678 --wait-for-client -m pytest -rPX -vv -s
```
(If you've activated `.venv` via `source .venv/bin/activate`, the bare `python -m pytest ...` form still works unchanged.)

## Run the type checker:

```bash
uv run mypy src/knowledgenet
```
Configuration lives in `pyproject.toml`'s `[tool.mypy]` section: `disallow_untyped_defs = true` is
enforced across the whole package (every module has a full typed interface). This is a single line
you can flip to `false` if strict typing gets in the way for some exploratory work — no per-module
bookkeeping needed either direction. CI (`.github/workflows/ci.yml`) runs this same command on every
push, so a clean local run means CI's type-check step will pass too.

## Build package artifacts:
Note: For all the commands below, you must cd to the project home directory.  

### Build API docs:

```bash
# Regenerate API `.rst` sources (excluding `src/knowledgenet/core`)
uv run sphinx-apidoc -f -e -o target/sphinx/apidoc src/knowledgenet src/knowledgenet/core

# Build HTML API docs
uv run sphinx-build -c src/api -D master_doc=modules -b html -d target/sphinx/doctrees target/sphinx/apidoc target/sphinx/html

# Build Markdown API docs (for agent knowledgebase ingestion)
uv run sphinx-build -c src/api -D master_doc=modules -b markdown -d target/sphinx/doctrees-markdown target/sphinx/apidoc target/sphinx/markdown

# Publish generated markdown docs in-repo for GitHub browsing
mkdir -p docs/api
find docs/api -maxdepth 1 -type f -name '*.md' -delete
cp -a target/sphinx/markdown/. docs/api/
```

Generated outputs:
  HTML: `target/sphinx/html`
  Markdown build output: `target/sphinx/markdown`
  Markdown published for GitHub: `docs/api`

## Publish package to PyPi:
Note: For all the commands below, you must cd to the project home directory.  
```bash
# Clean out dist/ first -- `uv build` does not do this, and `twine upload dist/*`
# below uploads everything in the directory, including artifacts left over from
# previous version builds. Skipping this risks accidentally re-uploading (or
# publishing to a different index) an old release.
rm -rf dist/

uv build
# Replace <repository> with either testpypi or pypi.
uv run twine upload --repository <repository> dist/*
```

Not yet adopted: `uv publish` (`uv publish --index testpypi` / `uv publish`, using the
`[[tool.uv.index]]` "testpypi" entry already in `pyproject.toml`) is a viable native replacement for
`twine upload` once we're ready to switch — it needs `UV_PUBLISH_TOKEN` set rather than `.pypirc`.
Sticking with `twine` for now; revisit later.

## Install git flow
We use git flow to manage branches and releases. On Fedora Linux, use the following commands to install the gitflow packages.The steps will differ based on what distribution and operating system you are using.
```bash
sudo dnf copr enable elegos/gitflow
sudo dnf install gitflow

git flow init -d
```

