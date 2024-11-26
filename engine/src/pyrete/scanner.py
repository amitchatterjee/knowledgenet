
import inspect
import sys
import os
import importlib

def ruledef(func):
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    wrapped.__wrapped__ = True
    return wrapped

def load_rules_from_module(module):
    decorated_methods = []
    for name, obj in inspect.getmembers(module):
        #print(f"{name}:{obj}")
        if inspect.isfunction(obj) and name != 'ruledef':
            if getattr(obj, '__wrapped__', False):
                obj()
                
    return decorated_methods

def __find_modules(path):
    modules = []
    for file in os.listdir(path):
        if file.endswith(".py") and not file.startswith("__"):
            module_name = file[:-3]  # Remove .py extension
            modules.append(importlib.import_module(module_name))
    return modules

def load_rules(path):
    sys.path.append(path)
    modules = __find_modules(path)
    for module in modules:
        load_rules_from_module(module)
