
import inspect
import sys
import os
import importlib
from ruleset import Ruleset
from repository import Repository
from util import to_tuple
from typing import Union

registry={}

def lookup(repository:str)->Repository:
    if repository not in registry:
        raise Exception('repository not found')
    rulesets=[]
    for ruleset_id, rules in registry[repository].items():
        rulesets.append(Ruleset(ruleset_id, rules))
    # Sort by id. The assumption is that the ids are defined in such a way that order can be determined. For example: 001-validation-rules, 002-business-rules, etc.
    rulesets.sort(key=lambda e: e.id)
    return Repository(repository, rulesets)

def ruledef(func):
    def wrapped(*args, **kwargs):
        rule = func(*args, **kwargs)
        if not rule.repository or not rule.ruleset:
            raise Exception('Both "repository" and "ruleset" must be specified')
        if rule.repository not in registry:
            registry[rule.repository] = {}
        if rule.ruleset not in registry[rule.repository]:
            registry[rule.repository][rule.ruleset] = []
        registry[rule.repository][rule.ruleset].append(rule)
        return rule
    wrapped.__wrapped__ = True
    return wrapped


def _load_rules_from_module(module):
    decorated_methods = []
    for name,obj in inspect.getmembers(module):
        #print(f"{name}:{obj}")
        if inspect.isfunction(obj) and name != 'ruledef':
            if getattr(obj, '__wrapped__', False):
                obj()                
    return decorated_methods

def _find_modules(path):
    modules = []
    for file in os.listdir(path):
        if file.endswith(".py") and not file.startswith("__"):
            module_name = file[:-3]  # Remove .py extension
            modules.append(importlib.import_module(module_name))
    return modules

def load_rules_from_filepaths(paths:Union[str,list,tuple]):
    paths = to_tuple(paths)
    for path in paths:
        sys.path.append(path)
        modules = _find_modules(path)
        for module in modules:
            _load_rules_from_module(module)

'''
import my_module
# Get the absolute path of the module
module_path = my_module.__file__ 
# Get the directory containing the module
module_dir = os.path.dirname(module_path)
'''
def load_rules_from_packages(packages:Union[str,list,tuple]):
    packages = to_tuple(packages)
    for package in packages:
        init_module = importlib.__import__(package)
        path = os.path.dirname(init_module.__file__)
        modules = _find_modules(path)
        for module in modules:
            _load_rules_from_module(module)
