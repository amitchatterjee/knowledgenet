# knowledgenet.scanner module

Rule discovery and registry utilities for declarative rule loading.

The scanner imports rule modules, executes functions marked with
`@ruledef`, and stores resulting Rule instances in an in-memory registry
organized as `registry[repository][ruleset] -> list[Rule]`.

### knowledgenet.scanner.clear() → None

Clear all discovered repositories, rulesets, and rules.

Useful for tests that need deterministic scanner state across runs.

### knowledgenet.scanner.load_rules_from_filepaths(\*paths: str) → None

### knowledgenet.scanner.load_rules_from_filepaths(paths: list[str] | tuple[str, ...]) → None

Discover and register rules from one or more filesystem paths.

Each imported module is inspected for `@ruledef`-decorated functions.
Accepts either one or more individual path strings, or a single list/tuple
of path strings – not a mix of the two.

### Example

Load rules from directory-based repositories before calling
[`lookup()`](#knowledgenet.scanner.lookup), either as separate arguments:

```default
load_rules_from_filepaths(
    'test/unit/scanner-rules/repo1/rs1',
    'test/unit/scanner-rules/repo1/override',
    'test/unit/scanner-rules/repo2/rs10',
)
```

or as a single list/tuple:

```default
load_rules_from_filepaths([
    'test/unit/scanner-rules/repo1/rs1',
    'test/unit/scanner-rules/repo1/override',
    'test/unit/scanner-rules/repo2/rs10',
])
```

### knowledgenet.scanner.load_rules_from_packages(packages: str | list | tuple) → None

Discover and register rules from importable package names.

Package roots are resolved via module `__file__` and then scanned for
sibling Python modules.

### knowledgenet.scanner.lookup(repositories: str | list | tuple, id: str | None = None) → [Repository](knowledgenet.repository.md#knowledgenet.repository.Repository)

Materialize a Repository from discovered registry entries.

* **Parameters:**
  * **repositories** – One repository id or a collection of repository ids to
    merge.
  * **id** – Optional id for the resulting Repository. Required when merging
    multiple source repositories.
* **Returns:**
  Repository with rulesets sorted lexicographically by ruleset id.

### Examples

Lookup one repository discovered via @ruledef modules:

```default
repo = lookup('repo1')
```

Compose multiple repositories into one execution plan:

```default
repo = lookup(['repo1', 'repo2'], id='composite')
```
