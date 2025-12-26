# For Developers
This page is meant for contributors of this project.

## One-time setup
This project needs python 3.14 or higher installed. It may work with other versions as well.  

### Create a virtual environment:
```bash
cd $HOME  
python3.14 -m venv knowledgenet-venv
```

### Switch to knowledgenet virtual environment:
```bash
source ~/knowledgenet-venv/bin/activate  
```
You can add the above to $HOME/.bashrc to automatically activate the venv.

## Install development tools:
```bash
pip install -U pytest pytest-cov    
pip install build  
pip install debugpy
pip install twine
```

## Install runtime dependencies:
```bash
  pip install -r requirements.txt

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
Note: For all the commands below, you must cd to the project home directory.  

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

## Build and install package:
Note: For all the commands below, you must cd to the project home directory.  
```bash
# bash
python -m build
pip install --force-reinstall dist/knowledgenet-*.whl
pip show knowledgenet
```

```powershell
# powershell
python -m build
pip install --force-reinstall (Get-ChildItem -Path dist/knowledgenet-*.whl).FullName
```

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


