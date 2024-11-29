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

![Simplistic Rules Network](./Rule Network.png)

### When to use Rete
Rete is not without it's own drawbacks. To start with, the algorithm is complex and application developers and business users need to understand how it works in order to design and develop rules that work efficiently and so that, it does not produce incorrect results. When asked to adopt Rete for building applications, many application developers ask the question - *why can't I use standard  constructs available on programming languages for developing the business logic (**switch/case**, **if-else**, etc.)?* This is a valid question. In fact, most simple decision-making business logic must use only standard constructs; Rete must be used only when the business process is very complex and evolving. For complex business logic, developing the application using standard constructs is likely to make the business logic very complex, difficult to maintain, difficult to train new people and error-prone. Also, keep in mind that often, requirements start out simple and grow complex over time. Another point to note is that, if business users author rules, application architects must ensure that proper design is in place to catch inefficiencies that a (non-technical) business user may inadvertently introduce. Most importantly, automated unit tests must be in place to test out the scenarios thoroughly before making the application generally-available.

## Definitions
The definitions, below, are used throughout this document and library. Note that they may not necessarily align with industry-standard terminologies.

**Service**: A service is the Rete engine/framework using which application developers and business users can automate decision making. By itself, the service does not make decisions. Combined with rules and facts, a service can automate a decision.  

**Facts**: Facts are objects that represent a "truth". Facts often constructed as objects that are instances of a classes. For example, an object that is an instance of class, *Person{}*, with attributes: *gender*, *age*, etc. can be used to model a human customer. Once populated with correct attributes, these objects may be passed in as inputs to the service; referred to as - **input facts**. Rules are executed against the input facts to produce **intermediate facts** or **result facts**. For complex decision making, intermediate facts are often produced when rules are executed, that are fed to another set of rules to produce more intermediate facts or final results. For example: when a rule, "determine_if_adult" is executed against a fact: Person(age = 10), it produces a fact that is an instance of a **Child{}** class. This object is then passed on as input to the rule, "sell_alcohol_to_adults_only" to produce a result fact that is an instance of class: **Sale{}** - Sale(allow=False). This is a trivial example to represent the concept. Very often, input facts in a complex decision making process goes through a network of rules to produce the result fact, or decision.

**FactSet**: All the facts that are part of the current execution. As mentioned above, new facts can be inserted, facts can be deleted or facts can be updated, 

**Rule**: A rule is defined as a set of conditions. If all the conditions are satisfied, a piece of code is executed, that may add new facts, update a fact, remove a fact, bypass the remaining rules, etc. The conditions are referred to as **When** or **Left Hand Side (LHS)** and the piece of code that is executed is called as **Then** clause or **Right Hand Side (RHS)**. The When part of the rule may contain one ore more **Condition** clauses. Each of these condition clauses identify a **class** that the clause is interested in and a "filter" **expression**, a piece of code that returns a True or False. All the condition clauses must return True in order for the Then clause to be executed. For example:

> Rule(id='determine_if_adult',  
        when=[  
            Condition(for_type=Person, matches_exp=lambda ctx: ctx.this.age <21)  
        ],  
        then=lambda ctx: insert(Child(...)))  

    Rule(id='sell_alcohol_to_adults_only',  
        when=[  
            Condition(for_type=Child, matches_exp=lambda ctx: True)  
        ],  
        then=lambda ctx: insert(Sale(allow=False, ...)))

    In the above example, Python *lambda expressions* are used. But references to functions may also be passed if the expressions are more complex. The insert() function, shown above, inserts a new fact into the FactSet.

In complex decision making applications, there may be many rules and many facts. The Pyrete engine manages the sequencing, execution and recursions of the rules. It also determines when the process is complete.
