# Pyrete Concepts
This document documents the underlying concepts that are used to construct this project. These concepts are not just implementation details, but are essential for application developers who are using or planning to use this library. **So, it is important for application developers to read this document closely**.

Pyrete is a Python Language software library that enables application developers to build applications that make complex decisions based on **facts** supplied to the entrypoint (or **service**) and **rules** developed by **application developers** and **business users**. At a high level, the service can be denoted as:

> Set\<result_facts> = service(Set\<input_facts\>, Collection\<rules\>)  
  where:  
  - **result_facts** are output(s) returned by the execution of the Pyrete engine.  
  - **input_facts** are input(s) to the Pyrete engine.  
  - **rules** are the rules coded in Python language that are provided to the Pyrete engine and executed by the engine to produce the output.

## Rete
Pyrete is an adaptation of the Rete algorithm designed by **Charles L. Forgy** of Carnegie Melon University. It is an efficient pattern matching algorithm that is widely used in many AI systems including Expert Systems. Unlike some other fields of AI like Machine Learning (ML), the results the Rete algorithm produce are more predictable and explainable. It also requires no learning as the algorithm is rule-based, i.e., predefined by "experts". Similar comparison also applies to statistical algorithms that are based on probabilistic model. In applications, Rete is often applied after ML and other statistical algorithms have processed the input data; the results from these process being fed to the Rete algorithm for higher accuracy and explainability.

### Inferencing
Rete emulates the process used by humans to come to a decision (or conclusion) based on facts presented to him/her/them. To make the decision, a person takes the facts provided to him/her and applies a set of well-established logic (or rules). For complex decision-making, applying a rule to a set of facts may produce intermediate facts that are then used as input to another set of rules. This process continues until the person reaches a decision. One can think of Rete as a network of rules that are applied to facts. A very **simplistic** representation of the Rete network is shown below.

![Simplistic Rules Network](./Rule-Network.drawio.png)

Note that the network shown above is very **simplistic**. First, real-life decision making involves many facts and many rules. Secondly, a rule does not just insert new facts, it can also modify existing facts and/or delete a facts. On any of these events, the flow may be modified and can even be moved backward to re-execute some of the earlier rules that were based on "incorrect" facts. So, the network is *cyclical* and *recursive* in nature, recursing through the rules in multiple passes in order to reach a decision. Contrast this type of network with acyclic flows like DAG (directed acyclic graph), commonly used in data pipelines.

For implementing a complex decision-making system, Rete networks are designed using one of the following strategies or a combination of both.

- **Forward Chaining**: In this type of implementations, the network starts with basic facts, applies rules to them to produce more "advanced facts" which are then used as inputs to additional rules and so on, until a decision is reached.
- **Backward Chaining**: In this type of implementations, the network uses the conclusions (or decisions) as input to the network and uses rules to eliminate one or more of the conclusions in order to reach a decision.

The Rete framework, like Pyrete, handles the sequencing of the rules and recursion through the network while business users and application developers create rules in isolation. 

### When to use Rete
Rete is not without it's own drawbacks. To start with, the algorithm is complex and application developers and business users need to understand how it works in order to design and develop rules that work efficiently and so that, it does not produce incorrect results. When asked to adopt Rete for building applications, application developers often ask the question - *why can't I use standard  constructs available on programming languages for developing the business logic (**switch/case**, **if-else**, etc.)?* This is a valid question. In fact, most simple decision-making business standard constructs are sufficient. Rete must be used only when the business process is very complex and evolving (or changing). For complex business logic, developing the application using standard constructs is likely to make the business logic very complex (spaghetti code), difficult to maintain, difficult to train new people and error-prone. Also, keep in mind that often, requirements start out simple and grow complex over time. Another point to note is that, if business users are designated to create rules, application architects must ensure that proper design is in place to catch inefficiencies that a (non-technical) business user may inadvertently introduce in the network. Most importantly, automated unit tests must be in place to test out the scenarios thoroughly before making the application generally-available.

## Definitions
The definitions, below, are used throughout this document and library. Note that they may not necessarily align with industry-standard terminologies.

### Service 
A service is the Rete engine/framework endpoint. Pyrete provides a "**execute(...)***" function to trigger rule execution on a set of facts.  

### Facts
Facts are objects that represent a "truth". Facts may have attributes that describe the characteristics of the fact.  In Pyrete, facts are instances of a classes and the characteristics are variables of the class. For example: 

```python
    class Person():
        def __init__(self, gender, age):
            self.gender = gender
            self.age = age
```
Note that facts may also include classes provided by python standard libraries like list, set, tuple, dict, etc. Pyrete includes a set of container classes to facilitate rule creation that operates on a group of facts. These classes are covered in a separate document.

### FactSet
A FactSet include all the facts that are part of the current execution of rules. As mentioned above, new facts can be inserted to the Factset, facts can be deleted from the Factset or facts can be updated by rule execution. 

### Rule
A rule is a set of conditions and an action that is performed when all the conditions are satisfied. The conditions are referred to as **When** or **Left Hand Side (LHS)** and the action is called as **Then** clause or **Right Hand Side (RHS)**. The action is a piece of Python code represented in a function or a lambda. Each of the conditions specify a **class** that the condition is interested in and a "filter" **expression**, a function or a lambda that returns either True or False. All the conditions must return True in order for the Then function to be executed. 

Pyrete provides library functions using which the Then function can insert, update and delete facts and functions that influence the Rete flow. It provides additional library functions that can be invoked from the Then expressions. These functions are covered in a separate document.

For example:
```python
Rule(id='determine_if_adult',  
        when=[  
            Condition(for_type=Person, matches_exp=lambda ctx: ctx.this.age <21)  
        ],  
        then=lambda ctx: insert(Child(...)))  

    Rule(id='sell_alcohol_to_adults_only',  
        when=[  
            Condition(for_type=Child, matches_exp=lambda ctx: True)  
        ],  
        then=lambda ctx: insert(Sale(allow=False, ...)))
```

In the above example, Python *lambda expressions* are used. But references to functions may also be passed if the expressions are more complex. The insert() function, shown above, inserts a new fact into the FactSet.

### Ruleset
A ruleset is a collection of rules. 
