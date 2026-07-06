# For Developers
This page is meant for contributors of this project.


> **Note:** For all the commands below, you must `cd` to the project home directory.  

## One-time setup
This project needs python 3.14 or higher installed. It may work with other versions as well.  

### Create a virtual environment:
```bash
python3.14 -m venv .venv
```

### Switch to knowledgenet virtual environment:
```bash
source .venv/bin/activate  
```
You can add the above to $HOME/.bashrc to automatically activate the venv when entering the project directory.

## Install development tools:

```bash
pip install --upgrade pip
pip install pip-tools
pip install -U --group=dev

```

## Install runtime dependencies:
```bash
mkdir -p target
python -m piptools compile pyproject.toml -o target/requirements.txt
pip install -r target/requirements.txt
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
python -m pytest -rPX -vv -s --cov  
# Without code coverage:  
python -m pytest -rPX -s -vv 
# With debug logging
python -m pytest -rPX -vv -s --log-cli-level=DEBUG  
# Run all tests on a pytest file:  
python -m pytest -rPX -vv -s 'test/unit/test_basic.py'  
# Run a single test:  
python -m pytest -rPX -vv -s 'test/unit/test_basic.py::test_one_rule_single_when_then'  
# Run tests with remote debugging:  
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m pytest -rPX -vv -s
```

## Build package artifacts:
Note: For all the commands below, you must cd to the project home directory.  

### Build API docs:

```bash
# Regenerate API `.rst` sources (excluding `src/knowledgenet/core`)
sphinx-apidoc -f -e -o target/sphinx/apidoc src/knowledgenet src/knowledgenet/core

# Build HTML API docs
sphinx-build -c src/api -D master_doc=modules -b html -d target/sphinx/doctrees target/sphinx/apidoc target/sphinx/html

# Build Markdown API docs (for agent knowledgebase ingestion)
sphinx-build -c src/api -D master_doc=modules -b markdown -d target/sphinx/doctrees-markdown target/sphinx/apidoc target/sphinx/markdown

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
Replace the <repository> with either testpypi or pypi.
# bash
python -m build
python -m twine upload --repository <repository> dist/*
```

## Install git flow
We use git flow to manage branches and releases. On Fedora Linux, use the following commands to install the gitflow packages.The steps will differ based on what distribution and operating system you are using.
```bash
sudo dnf copr enable elegos/gitflow
sudo dnf install gitflow

git flow init -d
```


