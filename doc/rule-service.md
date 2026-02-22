# Rule Service

This document explains how to build and configure a Knowledgenet rules application. It is intended for **platform engineers** who are responsible for setting up the rules infrastructure: bootstrapping the engine, defining the domain model, providing helper functions, configuring tracing, and wiring up transaction endpoints.

For writing and authoring individual rules, see the [Rules Authoring Guide](rules-authoring.md), which is intended for **rule authors**.

Please make sure that you read the [Concepts](concepts.md) before proceeding with this document.

**Note**: All instructions in this document assumes that we are using a **Linux** system terminal. Developers using Windows, MacOS and other systems will have to make some adjustments to the commands to suit the respective CLIs.

## Roles

In a Knowledgenet application, there are typically two sets of engineers:

1. **Platform Engineers** - Responsible for the application framework:
   - Designing and maintaining the domain model (fact classes)
   - Bootstrapping the Knowledgenet engine (loading rules, creating the service)
   - Writing helper and utility functions that rule authors use (e.g., action factories, configuration lookup, bypass logic)
   - Wiring up transaction endpoints (REST APIs, message queues, batch runners)
   - Loading and transforming input facts from external sources
   - Configuring tracing, logging, and monitoring
   - Setting up infrastructure facts (Collectors, EventFacts, Wrappers) that rules operate on

2. **Rule Authors** - Responsible for business logic:
   - Writing individual rules using the `@ruledef` decorator
   - Defining when-conditions and then-actions
   - Writing rule-specific helper functions (often co-located with the rule module)
   - Unit testing rules

This document covers the responsibilities of platform engineers. The [Rules Authoring Guide](rules-authoring.md) covers rule development.

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
The `knowledgenet-examples` companion project is designed to provide practical examples and a reference implementation of a typical Knowledgenet rules system. By exploring this repository, you can gain insights into how to structure and implement rules within the Knowledgenet framework and how to create a rules service. Please visit the [Knowledgenet Examples Repository](https://github.com/amitchatterjee/knowledgenet-examples), download/clone the repository to follow along.

To get started, you can clone the repository using the following command in your terminal:

```bash
git clone https://github.com/amitchatterjee/knowledgenet-examples.git
```
Once cloned, you can navigate through the project files and follow the examples provided to understand how to implement and work with Knowledgenet rules.

## Designing the Fact Model

Facts are the fundamental data units that rules operate on. As a platform engineer, you are responsible for designing the domain model -- the classes that represent facts in your business domain. Rule authors will use these classes in their when-conditions and then-actions.

### Basic Fact Classes
A fact class is a standard Python class. At minimum, it should have an `__init__` method and, for debugging purposes, `__str__` and `__repr__` methods:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __str__(self):
        return f"Person({self.name}, {self.age})"

    def __repr__(self):
        return self.__str__()
```

### Hash and Equality
Facts must be **hashable** because Knowledgenet stores them in sets internally. Python's default object identity (`id()`) satisfies this for most cases. However, if you need facts to be deduplicated based on their content (e.g., two `Person` objects with the same `id` field should be treated as the same fact), you must implement `__hash__` and `__eq__`:

```python
class Person:
    def __init__(self, id, name, age):
        self.id = id
        self.name = name
        self.age = age

    def __eq__(self, other):
        if isinstance(other, Person):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return f"Person({self.id}, {self.name})"

    def __repr__(self):
        return self.__str__()
```

**Important**: If you override `__eq__`, you **must** also override `__hash__`. Defining `__eq__` without `__hash__` makes the object unhashable, which will cause errors when Knowledgenet adds it to a set.

### Using Pydantic Models
For more structured fact definitions with built-in validation, you can use Pydantic `BaseModel` classes. The `knowledgenet-examples` auto-insurance project uses this approach:

```python
from pydantic import BaseModel, Field
from typing import Any

class Driver(BaseModel):
    id: str = Field(..., description="Unique driver identifier")
    name: str = Field(..., description="Driver full name")
    age: int = Field(..., description="Driver age")

    def __eq__(self, obj: Any) -> bool:
        if isinstance(obj, Driver):
            return self.id == obj.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return f'Driver({self.id})'

    def __repr__(self) -> str:
        return self.__str__()
```

### Built-in Python Types as Facts
Facts can also be instances of Python built-in types, as long as they are hashable. For example, `tuple`, `frozenset`, `int`, `str`, and `float` can all be used as facts directly:

```python
facts = [("key", "value"), frozenset([1, 2, 3]), 42]
result = service.execute(facts)
```

### Designing Input and Output Facts
A typical Knowledgenet application defines:

- **Input facts**: Represent the data for a single transaction. For example, in a claims processing system, input facts might include `Request`, `Claim`, `Policy`, and `Estimate` objects.
- **Output/result facts**: Represent the decisions made by rules. For example, `Action` facts that describe what action to take, or `ValidationError` facts that flag issues.
- **Intermediate facts**: Created by rules during execution to carry derived information between rule phases. These may or may not be part of the final result.

Rule authors should not need to understand how input facts are loaded -- they should be able to focus on the facts themselves and the business logic.

## Infrastructure Facts

In addition to domain-specific facts, the platform provides special infrastructure facts that enable aggregation, change tracking, and configuration.

### Collectors
A `Collector` groups facts of a particular type and provides aggregate functions (`sum()`, `size()`, `minimum()`, etc.). Platform engineers typically include Collectors in the input facts passed to `service.execute()`:

```python
from knowledgenet.container import Collector

# Create collectors as part of the input facts
def build_input_facts(request):
    facts = [request]
    # Add a collector so rules can aggregate Action facts
    facts.append(
        Collector(of_type=Action, group='action-collector',
                  value=lambda a: a.pay_amount,
                  key=lambda a: a.rank)
    )
    return facts
```

Collectors can also be inserted by rules at runtime. See the [Rules Authoring Guide](rules-authoring.md#collections-and-aggregation) for detailed usage.

### EventFacts
An `EventFact` monitors changes to specific fact types. When facts of the monitored types are inserted, updated, or deleted, the event is triggered and rules matching the event are evaluated:

```python
from knowledgenet.ftypes import EventFact

# Monitor when Action facts are created/modified
event = EventFact(group='onAction', on_types=Action)

# Include in input facts
facts = [request, collector, event]
```

Rule authors use `Event(group='onAction', ...)` in their when-clauses to react to these changes. See the [Rules Authoring Guide](rules-authoring.md#events) for details.

### Wrappers (Named Facts)
`Wrapper` facts allow you to pass configuration or context to rules without defining dedicated classes. Platform engineers commonly use them to provide ruleset-level context:

```python
from knowledgenet.ftypes import Wrapper

# Provide configuration for the validation ruleset
validation_ctx = Wrapper(
    named='validation-ruleset',
    description='Validation phase',
    rules_config={
        'missing_policy': {'reason': 'DENY', 'explanation': 'No policy found'},
        'insufficient_estimates': {'reason': 'DENY', 'explanation': 'Need 3+ estimates'}
    }
)

facts = [request, validation_ctx, collector, event]
```

Rule authors match these in their when-clauses: `Fact(named='validation-ruleset', var='ruleset_context')`.

## Providing Helper Functions for Rule Authors

Platform engineers should provide utility functions that simplify common operations for rule authors. These functions encapsulate logic that rule authors shouldn't need to reimplement, such as action creation, configuration lookup, and bypass handling.

A typical utility module might include:

```python
# util.py - provided by the platform team

from knowledgenet.controls import insert
from knowledgenet.ftypes import Wrapper

def create_action(ctx, ruleset_context, request):
    """Factory function to create an Action fact from ruleset configuration."""
    config = ruleset_context.rules_config.get(ctx._node.rule.id, {})
    action = Action(
        code=config.get('reason', 'UNKNOWN'),
        claim_id=request.claim.id,
        explanation=config.get('explanation', ''),
        pay_percent=config.get('pay_percent', 0),
        rank=config.get('rank', 0)
    )
    return action

def execute(ctx, ruleset_context, request):
    """Determine whether a rule should execute based on bypass flags."""
    rule_id = ctx._node.rule.id
    if rule_id in request.bypass:
        return False
    return True

def record_action_event(ctx, event):
    """Log action events for auditing."""
    for added in event.added:
        logging.info("Action created: %s", added)
    event.reset()
```

Rule authors then import and use these functions in their rules:

```python
@ruledef
def missing_policy():
    return Rule(
        run_once=True,
        when=[
            Fact(named='validation-ruleset', var='ruleset_context'),
            Fact(of_type=Request, var='request',
                 matches=lambda ctx, this: not this.policy)
        ],
        then=lambda ctx: insert(ctx, create_action(ctx, ctx.ruleset_context, ctx.request))
    )
```

## Bootstrapping the Knowledgenet Engine
There are two ways to initialize the Knowledgenet engine, initialize rulesets and rules, and get it ready to process transactions:
1. Programmatically.
1. Declaratively.

While, for smaller number of rulesets/rules, it is ok to use programmatic method, for systems with large numbers of ruleset/rules and where, the rules are deployed independently, the declarative method is more suitable.

### Programmatic initialization
See the code snippet below:

```python
from knowledgenet.rule import Collection, Rule, Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.helper import assign
from knowledgenet.controls import insert, delete, update, end
from knowledgenet.service import Service

from application.model import C1, C2, R1

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

Two rulesets: *rs1* and *rs2* were initialized with *rule_1_1*, *rule_1_2*, and *rule_1_3* belonging to *rs1* and *rule_2_1* belonging to *rs2*. When executing a transaction, *rs1* is executed first, followed by *rs2* as defined above.

### Declarative initialization
The declarative method is the preferred approach for large rule systems. Rules are defined in separate Python modules using the `@ruledef` decorator and organized into a directory structure. The Knowledgenet scanner discovers and loads them automatically.

Check out the [knowledgenet-examples/autoins/rules](https://github.com/amitchatterjee/knowledgenet-examples/autoins/rules) directory to see an example. Each subdirectory under the rules directory contains Python modules where rules are defined. The Knowledgenet service orders rulesets in ascending order of the subdirectory name.

#### The @ruledef decorator
The `@ruledef` decorator registers a rule function with the Knowledgenet rules registry. Each function decorated with `@ruledef` must return a `Rule` object that defines the conditions (when) and actions (then) for the rule. When a function is decorated with `@ruledef`, the decorator automatically extracts metadata based on the file's location -- the ruleset name is derived from the parent directory name and the rule name from the function name. For detailed information about writing rules with `@ruledef`, see the [Rules Authoring Guide](rules-authoring.md#declarative-rules-with-ruledef).

Here's a basic example:

```python
# Python module - my_first_rule.py
@ruledef
def my_rule():
    return Rule(
        when=Fact(of_type=MyType, matches=lambda ctx, this: some_condition),
        then=lambda ctx: some_action
    )
```

The decorator also accepts parameters to override the default naming conventions:

```python
@ruledef(id='different-ruleid', ruleset='different-rulesetId', repository='different-repoId', enabled=True)
def my_rule():
    return Rule(...)
```

This approach makes the rule authoring somewhat cumbersome to maintain when there are large number of rules but it allows you to break up rulesets and organize them in separate locations. You can also disable a rule by using the parameter - *enabled*.

#### Directory structure convention
When using `@ruledef` with automatic discovery, organize your rules in the following directory structure:

```
rules/
  <repository-name>/
    01_validation/
      validation_rules.py
      field_checks.py
    02_business/
      eligibility_rules.py
      pricing_rules.py
    03_finalization/
      selection_rules.py
```

- The top-level directory name becomes the **repository id**
- Each subdirectory name becomes a **ruleset id**, ordered alphabetically
- Each `.py` file contains rule definitions decorated with `@ruledef`

Prefixing directory names with numbers (e.g., `01_`, `02_`) ensures the desired execution order.

#### Loading rules

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
    load_rules_from_filepaths(rules_paths)

    rules_basename = os.path.basename(rules_path)
    repository = lookup(rules_basename)
    service = Service(repository)
    return service
```

Using the above method, rulesets and rules can be developed and deployed independently of the bootstrap code.

#### Repository merging
You can merge multiple repositories into a single repository. This allows rule teams to develop independently and combine their work:

```python
    repository = lookup(['repo1', 'repo2'], id='composite')
    service = Service(repository, id='some_name')
```

## Service Configuration

The `Service` constructor accepts optional parameters for advanced configuration:

```python
service = Service(
    repository,
    id="my-service",           # Service identifier for tracing/logging
    global_ctx={},             # Shared context accessible from all rules
    node_sorter=None           # Custom function to control node ordering
)
```

### Global Context
The `global_ctx` parameter provides a dictionary that is accessible from any rule's then-clause via the `global_ctx()` helper function. Use this to inject shared resources such as database connections, API clients, or configuration:

```python
service = Service(repo, global_ctx={
    'db_connection': db_conn,
    'api_client': api_client,
    'feature_flags': feature_flags
})
```

Rule authors access this in their rules:

```python
from knowledgenet.helper import global_ctx

def lookup_external_data(ctx):
    client = global_ctx(ctx)['api_client']
    result = client.lookup(ctx.request.id)
    insert(ctx, ExternalData(result))
```

### Custom Node Sorting
The `node_sorter` parameter allows you to override the default node ordering (which uses the `order` attribute on rules). This is an advanced feature for scenarios where the default ordering is insufficient:

```python
def custom_sorter(node_a, node_b):
    # Custom comparison logic
    return node_a.rule.order - node_b.rule.order

service = Service(repo, node_sorter=custom_sorter)
```

## Handling Rule Transactions
Once the service has been initialized, transactions are processed using the `Service.execute(...)` function. Example of an invocation is shown below:

```python
from knowledgenet.service import Service

def endpoint(request_data):
    # Load and transform input data into facts
    facts = load_facts(request_data)

    # Execute the service
    result_facts = service.execute(facts)

    # Extract and return decision facts
    actions = [f for f in result_facts if isinstance(f, Action)]
    return actions
```

See [rules_runner.py](https://github.com/amitchatterjee/knowledgenet-examples/blob/main/autoins/src/rule_runner.py) file in the knowledgenet-examples repository for a complete view of how the service is initialized and a batch transaction is invoked. Rule transactions can also be invoked from a web services endpoint, from a message queue, etc.

### Assembling Input Facts
Platform engineers are responsible for building the list of input facts for each transaction. This typically involves:

1. Loading domain facts from external sources (databases, APIs, files)
2. Adding infrastructure facts (Collectors, EventFacts, Wrappers)
3. Adding configuration/context facts for each ruleset

```python
def build_facts(request_data):
    # 1. Domain facts
    request = Request.from_dict(request_data)

    # 2. Infrastructure facts
    action_collector = Collector(of_type=Action, group='action-collector',
                                 value=lambda a: a.pay_amount, key=lambda a: a.rank)
    action_event = EventFact(group='onAction', on_types=Action)

    # 3. Ruleset context facts
    validation_ctx = Wrapper(named='validation-ruleset',
                             rules_config=load_rules_config('validation'))
    contract_ctx = Wrapper(named='contract-ruleset',
                           rules_config=load_rules_config('contract'))

    return [request, action_collector, action_event, validation_ctx, contract_ctx]
```

### Processing Results
The `service.execute()` call returns all facts present in the FactSet after rule execution completes -- both input facts and any facts inserted by rules. Platform engineers typically filter the results to extract the decision facts:

```python
result_facts = service.execute(input_facts)

# Extract decisions
actions = [f for f in result_facts if isinstance(f, Action) and not f.inactive]
errors = [f for f in result_facts if isinstance(f, ValidationError)]

if errors:
    return {'status': 'error', 'errors': [e.message for e in errors]}
else:
    return {'status': 'ok', 'actions': [a.to_dict() for a in actions]}
```

## Enable Tracing

The tracing capability of the Knowledgenet rules engine allows detailed traces of how the RETE network was executed in order to process the facts and produce the output. This is useful for troubleshooting rules issues and fine-tuning performances.

If you want tracing for rule execution, configure OpenTelemetry and initialize a tracer early in your application.

- Install runtime tracing packages manually. The packages you have to install will vary based on what kind of exporter you want to setup. Following is a sample:

```bash
python -m pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

```

- Initialize Open Telemetry from your application. The following code snippet is an example of OTEL initialization. There are different ways to initialize Open Telemetry tracing and controls how it behaves. Read the Open Telemetry documentation for details:


```python
import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def init_tracing(service_name: str = "[YOUR_APPLICATION_NAME]"):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)

# Create a root span and tell Knowledgenet to create trace spans
with tracer.start_as_current_span("transaction.execution - (CHANGE THE NAME of this span)"):
        result_facts = service.execute(facts, trc_level=10, trc_detail=10)
```

The tracing capability is extensive but it is an expensive operation. We suggest that you control it selectively instead of enabling it for all calls to *service.execute(...)*. You can control the stack depth and the details of the OTEL tracing span that Knowledgenet generates using the following parameters.

- *trc_level*: If *trc_level* is not specified, the default value, 0, is used, - tracing is disabled. The maximum value is 20. The higher the trace level, the higher the stack depth is (and slower).
- *trc_details*: If *trc_details* is not specified, the default value, 0, is used, - very little information is added to the trace span. The maximum value is 10. The higher the trace details, the more detailed the trace attributes are.

**Note:** By convention, *trc_level* less than or equal to 10 must be used to tune rules and application code. Higher trace levels are reserved for Knowledgenet tuning.

Knowledgenet provides a *knowledgenet.core.file_trace_exporter.FileSpanExporter* class that enables the trace spans to be written to a .ndjson file specified as the constructor argument.
