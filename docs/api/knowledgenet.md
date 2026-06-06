# knowledgenet package

## Submodules

* [knowledgenet.container module](knowledgenet.container.md)
  * [`Collector`](knowledgenet.container.md#knowledgenet.container.Collector)
    * [`Collector.add()`](knowledgenet.container.md#knowledgenet.container.Collector.add)
    * [`Collector.empty()`](knowledgenet.container.md#knowledgenet.container.Collector.empty)
    * [`Collector.maximum()`](knowledgenet.container.md#knowledgenet.container.Collector.maximum)
    * [`Collector.minimum()`](knowledgenet.container.md#knowledgenet.container.Collector.minimum)
    * [`Collector.remove()`](knowledgenet.container.md#knowledgenet.container.Collector.remove)
    * [`Collector.reset_cache()`](knowledgenet.container.md#knowledgenet.container.Collector.reset_cache)
    * [`Collector.size()`](knowledgenet.container.md#knowledgenet.container.Collector.size)
    * [`Collector.sum()`](knowledgenet.container.md#knowledgenet.container.Collector.sum)
    * [`Collector.variance()`](knowledgenet.container.md#knowledgenet.container.Collector.variance)
* [knowledgenet.controls module](knowledgenet.controls.md)
  * [`delete()`](knowledgenet.controls.md#knowledgenet.controls.delete)
  * [`end()`](knowledgenet.controls.md#knowledgenet.controls.end)
  * [`insert()`](knowledgenet.controls.md#knowledgenet.controls.insert)
  * [`next_ruleset()`](knowledgenet.controls.md#knowledgenet.controls.next_ruleset)
  * [`switch()`](knowledgenet.controls.md#knowledgenet.controls.switch)
  * [`update()`](knowledgenet.controls.md#knowledgenet.controls.update)
* [knowledgenet.decorator module](knowledgenet.decorator.md)
  * [`ruledef()`](knowledgenet.decorator.md#knowledgenet.decorator.ruledef)
* [knowledgenet.factset module](knowledgenet.factset.md)
  * [`Factset`](knowledgenet.factset.md#knowledgenet.factset.Factset)
    * [`Factset.add_facts()`](knowledgenet.factset.md#knowledgenet.factset.Factset.add_facts)
    * [`Factset.add_to_group_collectors_dict()`](knowledgenet.factset.md#knowledgenet.factset.Factset.add_to_group_collectors_dict)
    * [`Factset.del_facts()`](knowledgenet.factset.md#knowledgenet.factset.Factset.del_facts)
    * [`Factset.find()`](knowledgenet.factset.md#knowledgenet.factset.Factset.find)
    * [`Factset.update_facts()`](knowledgenet.factset.md#knowledgenet.factset.Factset.update_facts)
* [knowledgenet.ftypes module](knowledgenet.ftypes.md)
  * [`EventFact`](knowledgenet.ftypes.md#knowledgenet.ftypes.EventFact)
    * [`EventFact.reset()`](knowledgenet.ftypes.md#knowledgenet.ftypes.EventFact.reset)
  * [`Switch`](knowledgenet.ftypes.md#knowledgenet.ftypes.Switch)
  * [`Wrapper`](knowledgenet.ftypes.md#knowledgenet.ftypes.Wrapper)
* [knowledgenet.helper module](knowledgenet.helper.md)
  * [`assign()`](knowledgenet.helper.md#knowledgenet.helper.assign)
  * [`factset()`](knowledgenet.helper.md#knowledgenet.helper.factset)
  * [`global_ctx()`](knowledgenet.helper.md#knowledgenet.helper.global_ctx)
  * [`node()`](knowledgenet.helper.md#knowledgenet.helper.node)
  * [`session()`](knowledgenet.helper.md#knowledgenet.helper.session)
* [knowledgenet.node module](knowledgenet.node.md)
  * [`Leaf`](knowledgenet.node.md#knowledgenet.node.Leaf)
    * [`Leaf.execute()`](knowledgenet.node.md#knowledgenet.node.Leaf.execute)
  * [`Node`](knowledgenet.node.md#knowledgenet.node.Node)
    * [`Node.execute()`](knowledgenet.node.md#knowledgenet.node.Node.execute)
    * [`Node.reset_whens()`](knowledgenet.node.md#knowledgenet.node.Node.reset_whens)
* [knowledgenet.repository module](knowledgenet.repository.md)
  * [`Repository`](knowledgenet.repository.md#knowledgenet.repository.Repository)
* [knowledgenet.rule module](knowledgenet.rule.md)
  * [`Collection`](knowledgenet.rule.md#knowledgenet.rule.Collection)
  * [`Event`](knowledgenet.rule.md#knowledgenet.rule.Event)
  * [`Fact`](knowledgenet.rule.md#knowledgenet.rule.Fact)
  * [`Rule`](knowledgenet.rule.md#knowledgenet.rule.Rule)
* [knowledgenet.ruleset module](knowledgenet.ruleset.md)
  * [`Ruleset`](knowledgenet.ruleset.md#knowledgenet.ruleset.Ruleset)
* [knowledgenet.scanner module](knowledgenet.scanner.md)
  * [`clear()`](knowledgenet.scanner.md#knowledgenet.scanner.clear)
  * [`load_rules_from_filepaths()`](knowledgenet.scanner.md#knowledgenet.scanner.load_rules_from_filepaths)
  * [`load_rules_from_packages()`](knowledgenet.scanner.md#knowledgenet.scanner.load_rules_from_packages)
  * [`lookup()`](knowledgenet.scanner.md#knowledgenet.scanner.lookup)
* [knowledgenet.service module](knowledgenet.service.md)
  * [`Service`](knowledgenet.service.md#knowledgenet.service.Service)
    * [`Service.execute()`](knowledgenet.service.md#knowledgenet.service.Service.execute)
* [knowledgenet.util module](knowledgenet.util.md)
  * [`merge()`](knowledgenet.util.md#knowledgenet.util.merge)
  * [`of_type()`](knowledgenet.util.md#knowledgenet.util.of_type)
  * [`to_frozenset()`](knowledgenet.util.md#knowledgenet.util.to_frozenset)
  * [`to_list()`](knowledgenet.util.md#knowledgenet.util.to_list)
  * [`to_tuple()`](knowledgenet.util.md#knowledgenet.util.to_tuple)

## Module contents

Public package entrypoint for the Knowledgenet rules engine.

This package exposes the rule authoring DSL, scanner utilities, and service
runtime used to execute repositories of rulesets against transaction facts.

Typical transaction lifecycle:
1. Build or scan a Repository of Rulesets and Rules.
2. Initialize Service(repository).
3. Execute many transactions with `service.execute(input_facts)`.
4. Consume returned fact set containing original and derived facts.
