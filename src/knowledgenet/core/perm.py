def combinations(ll: list, include_only: list | None = None) -> list[list]:
    if not include_only:
        return cartesian(ll)
    # Build only the tuples containing >=1 element of include_only, in the same
    # order cartesian(ll) would produce them - not generate-then-filter. Callers
    # (Session._add_facts) insert these into the graph in this exact sequence,
    # and nodes sharing the same rule.order execute in insertion order, so
    # reordering here silently changes which fact-combination a rule processes
    # first among tied-priority matches.
    include_only_set = set(include_only)
    result: list[list] = []
    _append_matching(ll, 0, [], False, include_only_set, result)
    return result

def _append_matching(ll: list, i: int, prefix: list, satisfied: bool, include_only: set, result: list[list]) -> None:
    if satisfied:
        # Already guaranteed to qualify - nothing left to check, just build the rest.
        _append_all(ll, i, prefix, result)
        return
    if i == len(ll):
        return
    for x in ll[i]:
        _append_matching(ll, i + 1, prefix + [x], x in include_only, include_only, result)

def _append_all(ll: list, i: int, prefix: list, result: list[list]) -> None:
    if i == len(ll):
        result.append(prefix)
        return
    for x in ll[i]:
        _append_all(ll, i + 1, prefix + [x], result)

def cartesian(ll: list) -> list[list]:
    result: list[list] = [[]]
    for l in ll:
        result = [x + [y] for x in result for y in l]
    return result
