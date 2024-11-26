
import inspect
import sys
import os
import importlib

def ruledef(func):
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    wrapped.__wrapped__ = True
    return wrapped

# TODO this module only loads file modules. Need to support installed packages
'''
import my_module
# Get the absolute path of the module
module_path = my_module.__file__ 
# Get the directory containing the module
module_dir = os.path.dirname(module_path)

'''

def __load_rules_from_module(module):
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
        __load_rules_from_module(module)
