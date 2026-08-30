"""Rule discovery and registry utilities for declarative rule loading.

The scanner imports rule modules, executes functions marked with
``@ruledef``, and stores resulting Rule instances in an in-memory registry
organized as ``registry[repository][ruleset] -> list[Rule]``.
"""


import inspect
import logging
import sys
import os
import importlib
from typing import Union, overload

from knowledgenet.rule import Rule
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.util import to_tuple

registry: dict[str, dict[str, list[Rule]]] = {}

def clear():
    """Clear all discovered repositories, rulesets, and rules.

    Useful for tests that need deterministic scanner state across runs.
    """
    registry.clear()

def lookup(repositories:str|list|tuple, id:str=None)->Repository:
    """Materialize a Repository from discovered registry entries.

    Args:
        repositories: One repository id or a collection of repository ids to
            merge.
        id: Optional id for the resulting Repository. Required when merging
            multiple source repositories.

    Returns:
        Repository with rulesets sorted lexicographically by ruleset id.

    Examples:
        Lookup one repository discovered via @ruledef modules::

            repo = lookup('repo1')

        Compose multiple repositories into one execution plan::

            repo = lookup(['repo1', 'repo2'], id='composite')
    """
    if not isinstance(repositories, str) and not id:
        raise Exception("When multiple repositories are specified, a repository id must be provided")
    
    repositories = to_tuple(repositories)
    if not id:
        id = repositories[0]
    #print(registry)
    
    ruleset=[]
    for repository in repositories:
        if repository not in registry:
            raise Exception(f'repository: {repository} not found')
        
        for ruleset_id,rules in registry[repository].items():
            ruleset.append(Ruleset(ruleset_id, rules))
        
    # Sort by id. The assumption is that the ids are defined in alphabetical order. For example: 001-validation-rules, 002-business-rules, etc.
    ruleset.sort(key=lambda r: r.id)
    return Repository(id, ruleset)

def _load_rules_from_module(module):
    for name,obj in inspect.getmembers(module):
        if inspect.isfunction(obj):
            # Detect only functions explicitly marked as rule definitions.
            if getattr(obj, '__ruledef__', False):
                #print(f"{name}:{obj}")
                # Perform the following action only for functions that have been decorated with @ruledef
                rule = obj()
                if rule and type(rule) is not Rule:
                    raise Exception(f"Function {name} must return a Rule object")
                
def _find_modules(path):
    modules = []
    for file in os.listdir(path):
        if file.endswith(".py") and not file.startswith("__"):
            module_name = file[:-3]  # Remove .py extension
            # print(f"Loading module: {module_name}")
            modules.append(importlib.import_module(module_name))
    return modules

@overload
def load_rules_from_filepaths(*paths: str) -> None: ...
@overload
def load_rules_from_filepaths(paths: list[str] | tuple[str, ...]) -> None: ...
def load_rules_from_filepaths(*paths):
    """Discover and register rules from one or more filesystem paths.

    Each imported module is inspected for ``@ruledef``-decorated functions.
    Accepts either one or more individual path strings, or a single list/tuple
    of path strings -- not a mix of the two.

    Example:
        Load rules from directory-based repositories before calling
        :func:`lookup`, either as separate arguments::

            load_rules_from_filepaths(
                'test/unit/scanner-rules/repo1/rs1',
                'test/unit/scanner-rules/repo1/override',
                'test/unit/scanner-rules/repo2/rs10',
            )

        or as a single list/tuple::

            load_rules_from_filepaths([
                'test/unit/scanner-rules/repo1/rs1',
                'test/unit/scanner-rules/repo1/override',
                'test/unit/scanner-rules/repo2/rs10',
            ])
    """
    if len(paths) == 1:
        paths = to_tuple(*paths)

    for path in paths:
        #logging.info(f"Loading path: {path}")
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
    """Discover and register rules from importable package names.

    Package roots are resolved via module ``__file__`` and then scanned for
    sibling Python modules.
    """
    packages = to_tuple(packages)
    for package in packages:
        init_module = importlib.__import__(package)
        path = os.path.dirname(init_module.__file__)
        modules = _find_modules(path)
        for module in modules:
            _load_rules_from_module(module)
