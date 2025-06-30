# Rule Service

This document explains how to create a Knowledgenet rules application. Please make sure that you read the [Concepts](concepts.md) before proceeding with this document.

**Note**: All instructions in this document assumes that we are using a **Linux** system terminal. Developers using Windows, MacOS and other systems will have to make some adjustments to the commands the suit the respective CLIs. 

## Pre-requisites
In order to create services, you must be conversant with Python programming and best practices.

Install:
- Python 3.14 or higher - you may want to install the python-devel package in addition to the core package. We also recommend setting up a Python Virtual Environment (*venv*).   
- An IDE or text editor of your choice (e.g., VSCode, PyCharm).
- Access to the Knowledgenet Examples Repository.
- Optionally, install *git* as some of the commands shown below use git.

## Install Knowledgenet
To install Knowledgenet, run the following command: 
```bash
    pip install knowledgenet
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
1. Programmatically.
1. Declaratively.

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
The following code snippet initialized the rulesets and rules declaratively. The Python code containing the rules declarations are placed under the folder specified by the *rules_path* parameter passed to the *init_service()* function. Check out the [knowledgnet-examples/autoins/rules](https://github.com/amitchatterjee/knowledgenet-examples/autoins/rules) directory to see an example. Each subdirectory under this directory contains python modules where rules are defined. The Knowledgenet service orders rulesets in ascending order of the subdirectory name. The @ruledef decorator in Knowledgenet provides a simple way to define rules in a declarative manner. Each function decorated with @ruledef must return a Rule object that defines the conditions (when) and actions (then) for the rule. The when clause specifies facts or events that must match for the rule to fire, while the then clause defines the actions to take when the conditions are met. For detailed information about authoring rules, see the [Rules Authoring Guide](rules-authoring.md). When a function is decorated with @ruledef, it gets registered in the Knowledgenet rules registry for the appropriate repository and ruleset. The decorator automatically extracts metadata about the rule based on the file's location - the ruleset name is derived from the parent directory's name  and the rule name from the function name (my_rule) with the @ruledef decorator. 

In the code snippets below, the repository id is the folder name specified by the *rules_path*, each subdirectory name is the ruleset id for the ruleset. The rule id for the rule is *my_rule* - the function name. 

```python
import os

from knowledgenet.scanner import load_rules_from_filepaths, lookup
from knowledgenet.service import Service

def subdirs(parent):
    return [os.path.join(parent, name) for name in os.listdir(parent) if os.path.isdir(os.path.join(parent, name))]
    
def init_service(rules_path):
    rules_paths = []
    ruleset = subdirs(rules_path)
    for r in ruleset:
        rules_paths.append(r)
    scanner.load_rules_from_filepaths(rules_paths)

    rules_basename = os.path.basename(rules_path)
    repository = scanner.lookup(rules_basename)
    service = Service(repository)
```

Using the above method, rulesets and rules can be developed and deployed independently of the bootstrap code. 

#### Basic Rule Definition
Here's a basic example of creating a rule:

```python
# Python module - my_first_rule.py
@ruledef
def my_rule():
    return Rule(
        when=Fact(of_type=MyType, matches=lambda ctx, this: some_condition),
        then=lambda ctx: some_action
    )
```

#### Custom Rule Identification
The above approach allows rules authors to organize rules using function and folder names as conventions. It is possible to override repository, ruleset and rule ids instead of the convention. To override, use the ruledef parameters as shown in the example above:

```python
@ruledef(id='different-ruleid', ruleset='different-rulesetId', repository='different-repoId', enabled=True)
def my_rule():
    return Rule(
        ...
    )
```

This approach makes the rule authoring somewhat cumbersome to maintain when there are large number of rules but it allows you to break up rulesets and organize them in separate locations. You can also disable a rule by using the parameter - *enabled*.

#### Repository Merging
You can also merge multiple repositories into a single repository as follows:

```python
    repository = scanner.lookup(['repo1', 'repo2'], id='composite')
    service = Service(repository, id='some_name')
```

## Handling Rules Transactions
Once the service has been initialized, transactions are processed using the Service.execute(...) function. Example of an invocation is shown below:

```python
import sys
from knowledgenet.service import Service

...
def endpoint(...):
    # Load facts to be used
    facts = load_facts(...)

    # Execute the service
    result_facts = service.execute(facts, tracer=sys.stdout)

    # Do something with the result_facts
    ...
```

See [rules_runner.py](https://github.com/amitchatterjee/knowledgenet-examples/blob/main/autoins/rules/rules_runner.py) file in the knowledgenet-examples repository for a complete view of how the service is initialized and a batch transaction is invoked. Rules transaction can also be invoked from a web services endpoint, from a message queue, etc.
