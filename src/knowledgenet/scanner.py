
import inspect
import sys
import os
import importlib
from typing import Union

from knowledgenet.rule import Rule
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.util import to_tuple

registry={}

def lookup(repository:str)->Repository:
    #print(registry)
    if repository not in registry:
        raise Exception('repository not found')
    ruleset=[]
    for ruleset_id,rules in registry[repository].items():
        ruleset.append(Ruleset(ruleset_id, rules))
    
    # Sort by id. The assumption is that the ids are defined in alphabetical order. For example: 001-validation-rules, 002-business-rules, etc.
    ruleset.sort(key=lambda r: r.id)
    return Repository(repository, ruleset)

def ruledef(func):
    def wrapped(*args, **kwargs):
        rule = func(*args, **kwargs)
      
         # Override the rule ruleset and repository ids
        rule.id = func.__name__
        rule_path = os.path.dirname(inspect.getfile(func)).replace("/", os.sep).replace("\\", os.sep)
        splits = rule_path.split(os.sep)
        rule.ruleset = splits[-1]
        rule.repository = splits[-2]
        # print(f"Rule: {rule.id}, {rule.repository}, {rule.ruleset}")
        
        if rule.repository not in registry:
            registry[rule.repository] = {}
        if rule.ruleset not in registry[rule.repository]:
            registry[rule.repository][rule.ruleset] = []
        registry[rule.repository][rule.ruleset].append(rule)
        return rule
    wrapped.__wrapped__ = True
    return wrapped

def _load_rules_from_module(module):
    for name,obj in inspect.getmembers(module):
        #print(f"{name}:{obj}")
        if inspect.isfunction(obj) and name != 'ruledef':
            if getattr(obj, '__wrapped__', False):
                # Perform the following action only for functions that have been decorated with @ruledef
                rule = obj()
                if type(rule) is not Rule:
                    raise Exception(f"Function {name} must return a Rule object")
                
def _find_modules(path):
    modules = []
    for file in os.listdir(path):
        if file.endswith(".py") and not file.startswith("__"):
            module_name = file[:-3]  # Remove .py extension
            # print(f"Loading module: {module_name}")
            modules.append(importlib.import_module(module_name))
    return modules

def load_rules_from_filepaths(paths:Union[str,list,tuple]):
    paths = to_tuple(paths)
    for path in paths:
        # print(f"Loading path: {path}")
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
