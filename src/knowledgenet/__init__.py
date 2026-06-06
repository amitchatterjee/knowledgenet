"""Public package entrypoint for the Knowledgenet rules engine.

This package exposes the rule authoring DSL, scanner utilities, and service
runtime used to execute repositories of rulesets against transaction facts.

Typical transaction lifecycle:
1. Build or scan a Repository of Rulesets and Rules.
2. Initialize Service(repository).
3. Execute many transactions with ``service.execute(input_facts)``.
4. Consume returned fact set containing original and derived facts.
"""
