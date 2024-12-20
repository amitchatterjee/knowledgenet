# For Developers
This page is meant for contributors of this project.

## One-time setup
This project needs python 3.9 or higher installed. It may work with other versions as well.  

>> cd $HOME  
   python3.9 -m venv knowledgenet-venv

### To switch to knowledgenet virtual environment:
>> source ~/knowledgenet-venv/bin/activate  
\# You can add the above to $HOME/.bashrc to automatically activate the venv

## Install development tools:
>> pip install -U pytest pytest-cov    
   pip install build  
   pip install debugpy  

## Run tests - adjust as needed:
>> \# Note: For all the commands below, you must cd to the project home directory  
   \# With code coverage:  
   python -m pytest -rPX -vv --cov  
   \# Without code coverage:  
   python -m pytest -rPX -vv  
   \# Run all tests on a pytest file:  
    python -m pytest -rPX -vv 'test/UNIT/test_basic.py'  
   \# Run a single test:  
    python -m pytest -rPX -vv 'test/UNIT/test_basic.py::test_one_rule_single_when_then'  
   \# Run tests with remote debugging:  
   python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m pytest -rPX -vv 

## Build package:
>> python -m build

