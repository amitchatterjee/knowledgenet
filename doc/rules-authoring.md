# Rules Authoring

## Introduction
The Knowledgenet framework provides a flexible and powerful way to define, manage, and execute business rules in Python. This guide will walk you through the process of authoring rules using Knowledgenet, from basic rule creation to advanced patterns and best practices.

As discussed in [rules-service documentation](rules-service.md), Knowledgenet rules can be created in two ways:
1. **Programmatically** - by directly instantiating `Rule` objects in your initialization code.
2. **Declaratively** - using Python functions decorated with `@ruledef`, which automatically registers rules with the framework.

The declarative approach with `@ruledef` makes rules easier to write, test, and maintain as separate modules. Each rule consists of conditions (`when`) that determine when the rule should fire, and actions (`then`) that specify what should happen when those conditions are met. Rules are organized into rulesets and repositories, allowing for logical grouping and modular deployment of business logic.

## About the knowledgenet-examples companion project
The `knowledgenet-examples` companion project is designed to provide practical examples and a reference implementation of a typical Knowledgenet rules system. By exploring this repository, you can gain insights into how to structure and implement rules within the Knowledgenet framework. Please visit the [Knowledgenet Examples Repository](https://github.com/amitchatterjee/knowledgenet-examples), download/clone the repository to follow along. Here are some key functionalities and features you might find in the `knowledgenet-examples` project:

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

## Authoring a simple rule
