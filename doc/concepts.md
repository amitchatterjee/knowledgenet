# Pyrete Concepts
This document documents the underlying concepts that are used to construct this project. These concepts are not just implementation details, but are essential for application developers who are using or planning to use this library. **So, it is important for application developers to read this document closely**.

Pyrete is a Python Language software library that enables application developers to build applications that make complex decisions based on **facts** supplied to the entrypoint (or **service**) and **rules** developed by **application developers** and **business users**. The individuals or groups that create the rules are referred to as **authors". 

At a high level, the service can be denoted as:

> Set\<result_facts> = service(Set\<input_facts\>, Collection\<rules\>)  
  where:  
  - **result_facts** are output(s) returned by the execution of the Pyrete engine.  
  - **input_facts** are input(s) to the Pyrete engine.  
  - **rules** are the rules coded in Python language that are provided to the Pyrete engine and executed by the engine to produce the output.

## Rete
Pyrete is an implementation of an **Inference Engine** using an adaptation of the Rete algorithm designed by **Charles L. Forgy** of Carnegie Melon University. Rete is an efficient pattern matching algorithm that is widely used in many AI systems including Expert Systems. Unlike some other fields of AI like Machine Learning (ML), the results the Rete algorithm produce are more predictable and explainable. It also requires no learning as the algorithm is rule-based, i.e., predefined by "experts". Similar comparison also applies to statistical algorithms that are based on probabilistic model. In applications, Rete is often applied after ML and other statistical algorithms have processed the input data; the results from these process being fed to the Rete algorithm for higher accuracy and explainability.

### Inferencing
A Rete execution emulates the process used by humans to come to a decision (or conclusion) based on facts presented to him/her/them. To make the decision, a person takes the facts provided to him/her and applies a set of well-established logic (or rules). For complex decision-making, applying a rule to a set of facts may produce intermediate facts that are then used as input to another set of rules. This process continues until the person reaches a decision. One can think of Rete execution as a network of rules that are applied to facts in a certain order. A very **simplistic** representation of the Rete network execution is shown below.

![Simplistic Rules Network](./Rule-Network.drawio.png)

In the above diagram, the process starts at the top and ends at the bottom ,Note that the network shown above, is very **simplistic**. First, real-life decision making involves many facts and many rules. Secondly, a rule does not just insert new facts, it can also modify existing facts and/or delete a facts. On any change to the facts, the Rete execution flow may be modified and can even be moved backward to re-execute some of the earlier rules that were based on "incorrect" facts (assumptions). So, the network is *cyclical* and *recursive* in nature, recursing through the rules in order to reach a decision. Contrast this type of network with acyclic flows like DAG (directed acyclic graph), commonly used in data pipelines in data analytics and ETL applications.

For implementing an application that makes complex decisions, Rete networks are designed using one of the following strategies or a combination of them.

- **Forward Chaining**: In this type of implementations, the network starts with basic facts, applies rules to them to produce more "advanced" facts which are then used as inputs to additional rules and so on, until a decision is reached.
- **Backward Chaining**: In this type of implementations, the network uses the conclusions (or decisions) as input to the network and uses rules to eliminate one or more of the conclusions in order to reach a decision.

The Rete framework, like Pyrete, handles the sequencing of the rules and recursion through the network allowing rule authors focus on creating rules. A rule may be authored  in isolation and added to a Rete execution, the rules authors do not always have to understand the entire chain. 

### When to use Rete
Rete is not without it's own drawbacks. To start with, the algorithm is complex and authors need to understand how it works in order to design and develop rules that work efficiently and so that it does not produce incorrect results. When asked to adopt Rete for building applications, application developers often ask the question - *why can't I use standard  constructs available on programming languages for developing the business logic (**switch/case**, **if-else**, etc.)?* This is a valid question. In fact, most simple decision-making applications can be developed using standard constructs. Rete must be used only when the business process is very complex and evolving (or changing). For complex business logic, developing the application using standard constructs is likely to make the business logic very complex (spaghetti code) over time, difficult to maintain, difficult to train new people, and error-prone. Also, keep in mind that often, requirements start out simple and grow complex over time. Another point to note is that, if business users are designated to author rules, application architects must ensure that proper design is in place to catch inefficiencies that a (non-technical) business user may inadvertently introduce in the network. Most importantly, automated unit tests must be in place to test out the scenarios thoroughly before making the application generally-available.

## Definitions
The definitions, below, are used throughout this document and library. Note that they may not necessarily align with industry-standard terminologies.

### Service 
A service is the Pyrete Rete engine endpoint. Pyrete provides a "**execute(...)***" function to trigger rule execution on the Pyrete Inference Engine. An application may include multiple services for different types of decision making using different Knowledge Bases.

### Facts
Facts are information that represent a "truth". Facts may have attributes (often, referred to as **features**) that describe the characteristics of the fact. In Pyrete, facts are instances of a classes and the characteristics are variables of the class. For example: 

```python
    class Person():
        def __init__(self, gender, age):
            self.gender = gender
            self.age = age
```
Note that facts may also include classes and types provided by python built-in and external packages, as long as the types are hashable. For example, a fact can be of type - tuple, frozenset, etc.. Pyrete includes a set of container classes to facilitate rule creation that operates on a group of facts. These classes are covered in a separate document.

### FactSet
A FactSet include all the facts that are part of the current execution of rules. As mentioned above, new facts can be inserted to the Factset, facts can be deleted from the Factset or facts can be updated by rules during a Rete execution. 

### Rule
A rule is a set of conditions and an action that is performed when all the conditions are satisfied. The conditions are referred to as **When** or **Left Hand Side (LHS)** and the action is called as **Then** or **Right Hand Side (RHS)**. 

The action is a piece of Python code in the form of a function or a lambda. 

Each of the conditions need the following input parameters:
-  a **class**: specifies a class of facts the condition is interested in or operates on.
- a filter **expression**: a function or a lambda that returns either True or False. All the conditions must return True in order for the Then function to be executed. 

Normally, there is no need to specify the order in which the rules are executed because the Rete execution can figure that out. But it is possible to specify a run order and other hints to influence the execution. 

Pyrete provides library functions using which the Then function can insert, update and delete facts and functions that influence the Rete flow. It provides additional library functions that can be invoked from the Then expressions. These functions are covered in a separate document.

Here is an example of a simple rule definition:
```python
Rule(id='determine_if_adult',  
        when=[  
            Condition(of_type=Person, matches_exp=lambda ctx: ctx.this.age <21)  
        ],  
        then=lambda ctx: insert(Child(...)))  

    Rule(id='sell_alcohol_to_adults_only',  
        when=[  
            Condition(of_type=Child, matches_exp=lambda ctx: True)  
        ],  
        then=lambda ctx: insert(Sale(allow=False, ...)))
```

In the above example, Python *lambda expressions* are used. But references to functions may also be passed if the expressions are more complex. The insert() function, shown above, inserts a new fact into the FactSet.

### Ruleset
A ruleset is a collection of rules. For complex applications, the decision making process may require grouping the rules into rulesets and executing each ruleset in a specific flow. For example, rules may be classified in rulesets - validation rules, business rules and pricing rules. The requirement may be to run execute the rulesets in phases in the following manner.


![Rule Flow Example](./Rule-Flow.drawio.png)

With Pyrete, one can achieve that by classifying rules into rulesets and specifying the flow. Pyrete executes each ruleset in an **execution session**. On completion of a session, the facts from the output session are passed as inputs for the next session in the flow. A *Then* code on a rule in a ruleset can change the normal flow (shown using white arrows) by specifying which ruleset to execute next (show using red arrows). 

Example:
```python
Rule(id='end_execution', ruleset='validation_rules'  
        when=[  
            Condition(of_type=Validation, matches_exp=lambda ctx: not ctx.this.valid)  
        ],  
        then=lambda ctx: terminate())  
```

### Manual
A manual is a collection of rulesets. A manual is a repository of all the rules and rules for a decision-making service. When the function, service.execute(...) is invoked, Pyrete executes all the rulesets (and rules within the ruleset) and returns the result. Each call to the service.execute(...) function is referred to as a **Transaction**. 

The example below describes how manual can be organized and executed in sequence. In this example, a payment processing system makes a decision whether to pay the invoices it receives based on rules defined by the company's payment auditors. Each invoice is akin to an **transaction** (described below). In this case, think of the Manual as a rule book authored by the auditors - Ruleset as chapters and Rules as paragraphs.

> Manual: Payment Decision Manual
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

The manual component includes software data structures and code - rulesets and rules, that are defined during the development cycle of a project by rule authors. When the application is started, the manual components are initialized either programmatically or via configuration (as code) as explained in later.

### Transaction
Once the manual contents are initialized, the application is ready to process incoming transactions. Incoming transactions can be triggered by scheduled jobs or via requests received from a message broker, web services endpoints, etc. Each transaction must include a set of facts and reference to a manual. The combination of the facts and the manual is referred to as the **Knowledge Base**. The transaction process uses the knowledge base to come to a decision using the Rete algorithm. The output of this process is a set of (decision) facts. A transaction can be denoted as follows:  

> Set\<result_facts> = service.execute(Set\<input_facts\>, Manual)  

## Transaction Internals
Please refer to the diagram below while reading this section. It represents the various data structures and their relationship that Pyrete maintains as a part of a transaction.

![Pyrete Entity Relationship](./Pyrete-Entity-Relationship.drawio.png)

The blue boxes represent the entities that are created during the development phase (or authoring phase) and passed on to a transaction. The green box represents a service entrypoint. The red boxes represent the facts that are supplied to the entrypoint and other execution artifacts created in the process of executing the logic. As mentioned earlier, the **execute** function in the **service** module is the entrypoint for initiating a transaction. The pseudocode for the execution is shown below:

```
    # Handles ruleset execution flow
    service.execute(manual, facts):
        for each ruleset in the manual:
            session = create a session (ruleset, facts)
            result = session.execute(ruleset, facts) # See the pseudo function below.
            # Based on result from the above execution, continue to the next ruleset, break out of the loop, continue to another ruleset specified in the result
            if result contains a terminate directive:
                break
            else if result contains a continue_to(ruleset) directive:
                continue to the ruleset
            facts = result
        return facts

    session.execute(ruleset, facts):
        graph = create an empty graph
        for each rule in the ruleset:
            session.add_to_graph(graph, rule, facts) # See the pseudo function below.

        for each node in graph:
            changes = node.execute(node) # See the pseudo function below.

    node.execute(node):
        all_match = True
        all_cached = True
        for each condition in when:
            if matches_exp was evaluated earlier:
                match = cached match result
                cache = True
            else:
                match = execute matching_expo
                cache = False

            all_match = all_match and match
            all_cached = any_cached and cached

        if all_cached:
            return
        if all_matched:
            execute the then functions
            cache results
            return the results. the result returns the facts that were merged in by the then functions
                {inserted_facts: [...], updated_facts: [...], deleted_facts: [...]}
 

    session.add_to_graph(graph, rule, facts):
        types = get a list of for_types from the conditions on the When part of the rule

        for each type in types:
            matching_facts = get a list of facts that match the type

        combinations = create a list of all possible combinations
        # For example:
        # condition 1 of_type=A and facts [a, b] matches
        # condition 2 of_type=B and facts [x,y] matches
        # Then the combinations are:
        # (a,x), (a,y), (b,x), (b,y)

        for each combination in combinations:
            node = create a node
            add node to the graph
            # The engine determines the positions to insert the node into based on hints provided by the rule and other facts
```



