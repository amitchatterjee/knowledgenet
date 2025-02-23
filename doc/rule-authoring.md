# Rule Authoring

This document explains how Knowledgenet rules applications are implemented. Please make sure that you read the [Concepts](concepts.md) before proceeding with this document.

**Note**: All instructions in this document assumes that we are using a **Linux** system terminal. Developers using Windows, MacOS and other systems will have to make some adjustments to the commands the suit the respective CLI. 

## Pre-requisites
In order to write rules, you must be conversant with Python programming and best practices.

Install:
- Python 3.14 or higher - you may want to install the python-devel package in addition to the core package. We also recommend setting up a Python Virtual Environment (*venv*).   
- An IDE or text editor of your choice (e.g., VSCode, PyCharm).
- Access to the Knowledgenet Examples Repository.
- Optionally, install *git* as some of the commands shown below uses git.

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
The `knowledgenet-examples` companion project is designed to provide practical examples and a reference implementation of a typical Knowledgenet rules system. By exploring this repository, you can gain insights into how to structure and implement rules within the Knowledgenet framework. Please visit the [Knowledgenet Examples Repository](https://github.com/amitchatterjee.knowledgenet-examples), download/clone the repository to follow along. Here are some key functionalities and features you might find in the `knowledgenet-examples` project:

1. **Rule Definitions**: Examples of how to define rules using Python, including syntax and best practices.
2. **Rule Execution**: Demonstrations of how rules are executed within the Knowledgenet system.
3. **Integration**: Examples showing how to integrate Knowledgenet rules with other systems or applications.
4. **Testing**: Sample unit tests to ensure that rules are functioning as expected.
5. **Documentation**: Detailed comments and documentation within the code to explain the purpose and functionality of different components.

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
See the code segment below:

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

```python
def subdirs(parent):
    return [os.path.join(parent, name) for name in os.listdir(parent) if os.path.isdir(os.path.join(parent, name))]
    
def init_service(rulespath):
    rules_paths = []
    repo = subdirs(rulespath)
    for r in repo:
        rules_paths.append(r)
    scanner.load_rules_from_filepaths(rules_paths)

    rules_basename = os.path.basename(args.rulesPath)
    repository = scanner.lookup(rules_basename)
    service = Service(repository)
```