# Rule Service

This document explains how to create a Knowledgenet rules application. Please make sure that you read the [Concepts](concepts.md) before proceeding with this document.

**Note**: All instructions in this document assumes that we are using a **Linux** system terminal. Developers using Windows, MacOS and other systems will have to make some adjustments to the commands the suit the respective CLI. 

## Pre-requisites
In order to create services, you must be conversant with Python programming and best practices.

Install:
- Python 3.14 or higher - you may want to install the python-devel package in addition to the core package. We also recommend setting up a Python Virtual Environment (*venv*).   
- An IDE or text editor of your choice (e.g., VSCode, PyCharm).
- Access to the Knowledgenet Examples Repository.
- Optionally, install *git* as some of the commands shown below use git.

## Building Knowledgenet project from source
**At this time, the Knowledgenet engine has not been pushed to PyPi. So, you will need to build the project from source and install.**

To build the Knowledgenet project from source, you need to clone the repository from GitHub. Use the following command in your terminal:

```bash
git clone https://github.com/amitchatterjee/knowledgenet.git
```

Once the repository is cloned, navigate to the project directory:

```bash
cd knowledgenet
## Build and install package:
python -m build
pip install --force-reinstall dist/knowledgenet-*.whl
pip show knowledgenet
```

## About the knowledgenet-examples companion project
The `knowledgenet-examples` companion project is designed to provide practical examples and a reference implementation of a typical Knowledgenet rules system. By exploring this repository, you can gain insights into how to structure and implement rules within the Knowledgenet framework and how to create a rules service. Please visit the [Knowledgenet Examples Repository](https://github.com/amitchatterjee.knowledgenet-examples), download/clone the repository to follow along.

To get started, you can clone the repository using the following command in your terminal:

```bash
git clone https://github.com/amitchatterjee/knowledgenet-examples.git
```
Once cloned, you can navigate through the project files and follow the examples provided to understand how to implement and work with Knowledgenet rules.

## Bootstrapping the Knowledgenet engine
There are two ways to initialize the Knowledgenet engine, initialize rulesets and rules, and get it ready to process transactions:
 - Programmatically.
 - Declaratively.

While, for smaller number of rulesets/rules, it is ok to use programmatic method, for systems with large numbers of ruleset/rules and where, the rules are deployed independently, the declarative method is more suitable.

### Programmatic initialization
See the code snippet below:

```python
from knowledgenet.rule import Collection, Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert, delete, update
from knowledgenet.service import Service

from application.model import C1, R1, P1, Ch1
def init_service():
    rule_1_1 = Rule(id='r11',
                when=Fact(of_type=C1, matches=lambda ctx, this: assign(ctx, c1=this)),
                then=lambda ctx: insert(ctx, C2(ctx.c1.val)))
    rule_1_2 = Rule(id='r12',
                when=Fact(of_type=C2, matches=lambda ctx, this: this.val > 10),
                then=lambda ctx: end(ctx))
    rule_1_3 = Rule(id='r13', order=1,
                when=Fact(of_type=C2, matches=lambda ctx, this: True),
                then=lambda ctx: insert(ctx, R1('r13')))
    rule_2_1 = Rule(id='r21',
                when=Fact(of_type=C2, matches=lambda ctx, this: True),
                then=lambda ctx: insert(ctx, R1('r21')))
    repo = Repository('repo1', [
        Ruleset('rs1', [rule_1_1, rule_1_2, rule_1_3]), 
        Ruleset('rs2', [rule_2_1])])
    service = Service(repo)
    return service
```

Two rulesets: *rs1* and *rs2* were initialized with *rule_1_1* and *rule_1_2* belonging to *rs1* and *rule_2_1* and *rule_2_2* belonging to *rs2*. When executing a transaction, *rs1* is executed first, followed by *rs2* as defined above.

### Declarative initialization
The following code snippet creates a service declaratively. The Python code containing the rules are placed under the folder specified by the *rulespath* parameter passed to the *init_service()* function. Check out the [knowledgnet-examples/autoins/rules](https://github.com/amitchatterjee/knowledgenet-examples/autoins/rules) directory to see an example. Each subdirectory under this directory contains rule definitions for a ruleset. The Knowledgnet service orders rulesets in ascending order of the subdirectory name. 

```python
import os

from knowledgenet.scanner import load_rules_from_filepaths, lookup
from knowledgenet.service import Service

def subdirs(parent):
    return [os.path.join(parent, name) for name in os.listdir(parent) if os.path.isdir(os.path.join(parent, name))]
    
def init_service(rules_path):
    rules_paths = []
    repo = subdirs(rules_path)
    for r in repo:
        rules_paths.append(r)
    scanner.load_rules_from_filepaths(rules_paths)

    rules_basename = os.path.basename(rules_path)
    repository = scanner.lookup(rules_basename)
    service = Service(repository)
```

Using this method, rulesets and rules can be developed and deployed independently of the bootstrap code.  

## Handling Rules Transactions
Once the service has been initialized, transactions are processed using the Service.execute(...) function. Example of an invocation is shown below:

```python
import sys
from knowledgenet.service import Service

...
def enpoint(...):
    # Load facts to be used
    facts = load_facts(...)

    # Execute the service
    result_facts = service.execute(facts, tracer=sys.stdout)

    # Do something with the result_facts
    ...
```

See [rules_runner.py](https://github.com/amitchatterjee/knowledgenet-examples/blob/main/autoins/rules/rules_runner.py) file in the knowledgenet-examples repository for a complete view of how the service is initialized and a batch transaction is invoked. Rules transaction can also be invoked from a web services endpoint, from a message queue, etc. 
