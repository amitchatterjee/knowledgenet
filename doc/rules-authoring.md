# Rules Authoring

## Introduction
The Knowledgenet framework provides a flexible and powerful way to define, manage, and execute business rules in Python. This guide will walk you through the process of authoring rules using Knowledgenet, from basic rule creation to advanced patterns and best practices.

As discussed in [rules-service documentation](rules-service.md), Knowledgenet rules can be created in two ways:
1. **Programmatically** - by directly instantiating `Rule` objects in your initialization code.
2. **Declaratively** - using Python functions decorated with `@ruledef`, which automatically registers rules with the framework.

The declarative approach with `@ruledef` makes rules easier to write, test, and maintain as separate modules. Rules are organized into rulesets and repositories, allowing for logical grouping and modular deployment of business logic.

## About the knowledgenet-examples companion project
The `knowledgenet-examples` companion project is designed to provide practical examples and a reference implementation of a typical Knowledgenet rules system. By exploring this repository, you can gain insights into how to structure and implement rules within the Knowledgenet framework. Please visit the [Knowledgenet Examples Repository](https://github.com/amitchatterjee/knowledgenet-examples), download/clone the repository to follow along. Here are some key functionalities and features you might find in the `knowledgenet-examples` project:

1. **Rule Definitions**: Examples of how to define rules using Python, including syntax and best practices.
2. **Rule Execution**: Demonstrations of how rules are executed within the Knowledgenet system.
3. **Integration**: Examples showing how to integrate Knowledgenet rules with other systems or applications.
4. **Testing**: Sample unit tests to ensure that rules are functioning as expected.
5. **Documentation**: Detailed comments and documentation within the code to explain the purpose and functionality of different components.

To get started, you can clone the repository using the following command from your terminal:

```bash
git clone https://github.com/amitchatterjee/knowledgenet-examples.git
```
Once cloned, you can navigate through the project files and follow the examples provided to understand how to implement and work with Knowledgenet rules.

## Rule Structure
A rule consists of three main components:

1. **Rule Attributes** - Properties that control rule behavior:
   - `id`: A globally-unique identifier for the rule
   - `order`: Controls execution priority (nodes with lower numbers execute first). See the [concepts documentation](concepts.md) for details on what a *node* is. If not specified, default value of *0* is used
   - `run_once`: If True, each node for the rule only executes once and is never activated again, If not specified, default value of *False* is used
   - `retrigger_on_update`: Controls whether the node is re-evaluated when one or more of the facts present in the *when* clause are updated by the *then* clause of the rule. If not specified, default value of *True* is used

2. **When (Conditions)** - Define when the rule should fire:
   - Can specify single or multiple conditions using `Fact` or `Collection`
   - Each condition can include a `matches` lambda/function for filtering. If not included, default value of *True* is used (the condition will always be satisfied as long as a fact of that type is present)
   - Can use `var` parameter to store matched facts in the context

3. **Then (Actions)** - Define what happens when conditions are met:
   - Can be a single function/lambda or list of functions/lambdas
   - Functions receive a context object containing matched facts
   - Common actions performed: `insert()`, `update()`, `delete()` to insert new facts, update an existing fact or delete a fact
