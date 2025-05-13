# Knowledgenet Concepts
This document describes the underlying concepts of the knowledgenet rules engine. These concepts are not just implementation details, but are essential for application architects and developers, who are using or planning to use this library. **So, it is important for application developers to read this document completely in order to create an efficient and effective system.**.

Knowledgenet is a Python Language software library that enables application developers to build applications that make complex decisions based on **facts** supplied to the service entrypoint and **rules** developed by **application developers** and **business users**. The individuals or groups that create the rules are often referred to as rule **authors"**. With the increased use of *Generative AI*, AI programs can also be rule authors.

At a conceptual level, the entrypoint to this service can be represented by the pseudo-function:

> entrypoint(input_facts:set, rules:tuple) -> result_facts:set  
  where:  
  - **result_facts** are output(s) of the Knowledgenet engine.  
  - **input_facts** are input(s) to the Knowledgenet engine.  
  - **rules** are code segments in Python language that are provided to the Knowledgenet engine. The Knowledgenet engine executes of the rules in order to produce the output.

## RETE
Knowledgenet is an implementation of an **Inference Engine** using an adaptation of the **RETE** algorithm designed by **Charles L. Forgy** of Carnegie Melon University. RETE is an efficient pattern matching algorithm that is widely used in many AI systems including Expert Systems. Unlike some other fields of AI like Machine Learning (ML), the results the RETE algorithm produce are fully predictable and explainable. It also requires no "learning" as the algorithm is rule-based, predefined by "experts". Similar comparison also applies to statistical algorithms that are based on probabilistic model. In applications, RETE is often applied after ML and other statistical algorithms have processed the input data; the results from these process, being fed to the RETE algorithm for higher accuracy and explainability.

### Inferencing
A RETE execution emulates the process used by humans to come to a decision (or conclusion) based on facts presented to him/her/them. To make the decision, a person takes the facts provided to him/her and applies a set of well-established logic (or rules). For complex decision-making, applying a rule to a set of facts may produce *intermediate* facts that are then used as input to another set of rules. This process continues until a decision or a set of decisions are reached. One can think of RETE execution as a network of rules that are applied to facts in a certain order based on the availability of facts. A very **simplistic** representation of the RETE network execution is shown below.

![Simplistic Rules Network](./Rule-Network.drawio.png)

In the above diagram, the execution starts at the top and ends at the bottom. Note that the network shown above, is very **simplistic** and does not represent how rules are executed. First, real-life decision making involves many facts and many rules. Secondly, a rule does not just insert new facts, it can also modify existing facts and/or delete a facts. On any change to the facts, the RETE execution flow may be modified and can moved backward to re-execute some of the earlier rules that were based on "incorrect" facts (assumptions). So, the network can be *cyclical* and *recursive* in nature, recursing through the rules in order to reach a decision. Contrast this type of network with acyclic flows like DAG (directed acyclic graph), commonly used in data pipelines in data analytics and ETL applications.

For implementing an application that makes complex decisions, RETE networks are designed using one of the following design strategies or a combination of them.

- **Forward Chaining**: In this strategy, the network starts with basic facts, applies rules to them to produce more "advanced" facts which are then used as inputs to additional downstream rules and so on, until a decision is reached.
- **Backward Chaining**: In this strategy, the network starts with conclusions (or decisions) as input to the network and uses rules to eliminate one or more of the conclusions in order to reach a decision.

A RETE engine, like the knowledgenet engine, handles the sequencing of the rules and recursion through the network, allowing rule authors focus on creating rules. A rule can be authored in isolation and added to the pool of rules for RETE execution; the rules authors do not always need to understand the entire execution chain. 

### When to use RETE
When asked to adopt RETE for building applications, application developers often ask the question - *why can't I use standard  constructs available on programming languages for developing the business logic (**switch/case**, **if-else**, etc.)?* This is a valid question. In fact, most simple decision-making applications can be developed using standard constructs of a programming language. RETE must be used only when the business process is very complex and evolving (or changing). For complex business logic, developing the application using standard constructs is likely to make the code very complex ("spaghetti") over time, difficult to maintain, difficult to train new people, and error-prone. Also, keep in mind that often, requirements start out simple and grow complex over time.

RETE is not without it's own drawbacks. To start with, the algorithm is complex and architects and authors need to basic understand how it works fairly well in order to design and develop rules that work efficiently and that does not produce incorrect results. Another point to keep in mind is that, if business users are designated to author rules, application architects must ensure that proper architecture is in place to catch inefficiencies that a (non-technical) business user may inadvertently introduce in the network. Most importantly, automated unit tests must be in place to test out the scenarios thoroughly before making the rules generally-available.

## Definitions
The definitions, below, are used throughout this document and library. Note that the terms may not necessarily align with industry-standard terminologies.

### Service 
A service is the Knowledgenet RETE engine endpoint. The service must be initialized during application startup. A service is associated with a single rule repository (see **repository** definition below). Once initialized, the service can be invoked using the **execute(...)** function and by passing facts (explained below). Each execution is referred to as a **service transaction**. An application may consist of one or more services but most commonly, an application consists of a single service.

### Facts
Facts are information that represent a "truth". Facts may have attributes (often, referred to as **features**) that describe the characteristics of the fact. In Knowledgenet, facts are instances of a classes and the characteristics are variables/attributes of the class. For example: 

```python
class Person():
    def __init__(self, gender, age):
        self.gender = gender
        self.age = age
```
Note that facts may also include classes and types provided by python built-in and external packages, as long as the types are hashable. For example, a fact can be of type - tuple, frozenset, etc.. Knowledgenet includes a set of container classes to facilitate rule creation that operates on a group of facts. These classes are covered in a rules authoring document.

### FactSet
A FactSet include all the facts that are part of the current execution of rules. During execution of a service transaction, facts are passed to service as parameters. As mentioned above, new facts can be inserted into the Factset, facts can be deleted from the Factset or facts can be updated by rules during a RETE execution. 

### Rule
A rule is a code consisting of a set of conditions and one or more actions that are performed when all the conditions are satisfied. The conditions are referred to as **When** or **Left Hand Side (LHS)** and the actions are referred to as **Then** or **Right Hand Side (RHS)**. 

A condition needs the following input parameters:
-  a **type**: specifies a class/type of facts the condition operates on.
- a filter/match **expression** that returns either *True* or *False*. When the rule is executed by the RETE engine, all the conditions must return *True* in order for the Then to be executed. It is possible to specify a run order and other hints to influence the execution. 

Knowledgenet provides helper functions using which the *Then* functions can insert, update and/or delete facts and functions that a rule can use to influence the RETE flow. It provides additional library functions that can be invoked from the *When* and *Then* functions/expressions. These functions are covered in rules authoring document.

Here is an example of a simple rule definition:
```python
Rule(id='determine_if_adult',  
        when=Fact(of_type=Person, matches=lambda ctx, this: this.age <21),  
        then=lambda ctx: insert(Child(...)))  

    Rule(id='sell_alcohol_to_adults_only',  
        when=Fact(of_type=Child, matches=lambda ctx: True),  
        then=lambda ctx: insert(Sale(allow=False, ...)))
```

In the above example, Python *lambda expressions* are used. But references to functions may also be passed if the expressions are more complex and not compatible with lambda syntax. The insert() function, shown above, inserts a new fact into the FactSet.

### Ruleset
A ruleset is a collection of rules. For complex applications, the decision-making process may require organizing the rules in rulesets and executing each ruleset in a specific order. For example, "validation" rules may be classified in a ruleset as do "business rules" and "pricing rules". The requirement may be to execute the rulesets in phases in the following manner.

![Rule Flow Example](./Rule-Flow.drawio.png)

With Knowledgenet, this can be achieved by organizing the rules into rulesets and specifying the flow. Knowledgenet executes each ruleset in an **execution session**. On completion of a session, the facts from the output session are passed as inputs for the next session in the flow. A *Then* code on a rule can change the normal flow (shown using white arrows) by specifying which ruleset to execute next (shown using red arrows). 

Example:
```python
Rule(id='end_execution', ruleset='validation_rules'  
        when=[  
            Fact(of_type=Validation, matches=lambda ctx, this: not this.valid())  
        ],  
        then=lambda ctx: end(ctx))  
```

### Repository
A repository is a collection of rulesets for a decision-making service. When a service transaction is invoked, Knowledgenet executes all the rulesets (and rules within the ruleset) and returns the result. 

The example below, describes how repository can be organized and executed in sequence. In this example, a payment processing system makes a decision whether to pay for the received invoices based on rules defined by the company's payment experts. Each invoice is processed in a service transaction as described below. In this case, you can think of the Repository as a rule book authored by the payment auditors, Ruleset as chapters, and Rules as paragraphs.

> Repository: Payment Decision Manual
> - Ruleset: Validation
>    - Rule: Invoice is complete (Rule)
>       - Condition: All mandatory fields of the invoice are entered
>       - Condition: All fields have valid data types and sizes
>    - Rule: Invoice is from a valid vendor
>       - Condition: The vendor is in approved vendors list
>       - Condition: The bank account of the vendor matches
> - Ruleset: Eligibility
>   - Rule: Duplicate
>       - Condition: The invoice does not match any previously-paid invoice
>   - Rule: Overpayment
>       - Condition: The vendor owes the company money
> - Ruleset: Payment
>   - Rule: Contract    
>       - Condition: The amount matches contracted rate
> - ...

The repository includes data structures declarations for facts and rules code, that are defined during the development cycle of a project by rule authors. When the application is started, repositories are initialized either programmatically or via configuration as explained in rules authoring document.

### Transaction
Once a service is initialized using a rule repository, the application is ready to process incoming transactions. Incoming transactions can be triggered by scheduled jobs or via requests received from a message broker, web services endpoints, etc. Each transaction must include a set of facts. The facts and the repository combo is referred to as the **Knowledge Base**. The transaction process executes rules in the repository to produce decisions using the RETE algorithm. The output of this process is a set of (decision/result) facts. A service can execute many transactions. A transaction can be represented in a pseudocode as follows:  

> \# Init - one time
>  service = Service(repo:Repository)
>
>  \# Transaction processing - many times
>  result_facts:set = service.execute(input_facts:set)  

## Transaction Internals
Please refer to the diagram below. It represents Knowledgenet's internal data structures and their relationships.

![Knowledgenet Entity Relationship](./Knowledgenet-Entity-Relationship.drawio.png)

The blue blocks represent the entities that are created during the development phase (or "authoring phase") and is passed as input parameters when creating the service. The green arrow represents a service entrypoint for initiating a transaction. The red blocks represent the input facts that are supplied to a transaction and other execution artifacts created in the process of processing the transaction. As mentioned earlier, the **execute** function in the **knowledgenet.service.Service** class is the entrypoint for a transaction. It is a synchronous call.  

When the service is initialized, the initialization logic orders the rules in the rulesets based on rule definitions to process transactions.

It is important to understand the concept behind a few of the *blocks* in the diagram.

### Node
A node can be thought of as an instance of a rule. On initialization and after execution of each node, the knowledgenet rules engine examines the facts specified in the *when* clause of a rule and creates a combination of facts that match the facts specified in the *when* declaration. The rules engine creates a node object for each of these combinations and places them in an execution graph, explained below.

### Leaf
A leaf can be thought of as an instance of each *when* condition. As explained above, a node contains one or more leaves, each associated with a particular fact object.

### Graph
The nodes that are created during initialization of a transaction, and, as a byproduct of node execution, are placed in an execution graph and scheduled for execution. The node execution involves evaluation of the *when* condition(s) and execution of the *then* condition when all the *when* condition matches. The nodes are placed in the graph, ordered by the *order* parameter specified in the rule definition. The nodes are executed in the ascending order using a cursor. Typically, the cursor moves in the forward direction, but depending on the facts created, updated or deleted during a node execution, the cursor may be moved in backward direction. The execution cycle comes to an end when the last node is executed.

### Service Execution
For every transaction, knowledgenet.service.Service.execute() is invoked. Knowledgenet executes rules that are a part of the first ruleset. The supplied facts are passed in as parameters to the execute() function. The facts that returned from the execution of the first ruleset are passed on to the next ruleset. Note that the facts that were passed into the first ruleset is returned by the service execution unless it is explicitly removed by rules in the ruleset. The output from the second ruleset is passed on as input to the third ruleset. This process continues until all rulesets are executed. The resulting facts are returned to the caller.

### Ruleset Execution (Session)
The ruleset execution function is responsible for executing the rules on the graph and managing the changes to the facts during the session. This function is the core implementation of the RETE algorithm. In the diagram above, the execution environment is referred to as a **Session**.  Here's a step-by-step explanation of how it works:

1. **Session Initialization**:
    - An empty execution graph is initialized.
    - Initial facts are loaded. Based on the facts, nodes are created and added to the graph. The position where a node is inserted depends on the rule definition.
    - A cursor is set to the leftmost element in the graph.

2. **Node Execution**:
    - The rule associated with the node that the cursor points to, is executed. The rule execution involves the following steps:
      - Knowledgenet evaluates each of the *when* matching expressions. (The result of each *when* function is cached so that they are not evaluated unless the facts have been updated). 
      - If all the *when* functions on the result returns *True*, the *then* functions are executed. The result is also cached.
    - If the rule is marked to run only once (`run_once`), the element is deleted from the graph.

3. **Handling Changes from Node Execution**:
    - After execution of each node, Knowledgenet checks if the rules executions signalled changes as itemized below. These changes are are processed immediately before executing the next node:
        - **Delete**: If a fact is deleted by the rule *then* function, all nodes containing the deleted fact is removed from the graph.
        - **Insert**: If new facts were inserted, new nodes are added to the graph similar to how nodes are added during initialization.
        - **Update**: If facts were updated, all nodes containing the fact is invalidated in preparation for re-execution of the node.
        - **Break**: If a 'break' is signaled, the session execution is terminated, The ruleset execution logic terminates the transaction and returns the facts.
        - **Switch**: If a 'switch' is signaled, the session execution is terminated. The ruleset execution logic examines the switch to determine the next ruleset to proceed.

    For each of the above cases, the cursor is adjusted to move to the position of the leftmost node affected by the change. If there were no changes, the cursor is moved forward and the next node is executed as described above

4. **Returning Results**:
    - The facts that are present in the Factset after all the nodes are executed, are returned.
