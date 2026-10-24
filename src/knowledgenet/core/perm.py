def combinations(ll: list, include_only: list | None = None) -> list[list]:
    if not include_only:
        return cartesian(ll)
    # Equivalent to [c for c in cartesian(ll) if any(x in include_only for x in c)],
    # but built directly rather than generating the full cartesian product and
    # discarding most of it. _append_matching walks the same choices, in the
    # same nested order (ll[0] outermost, ll[-1] innermost), that cartesian()
    # does - so the tuples that do qualify come out in exactly the order a
    # filtered cartesian(ll) would have produced them. Callers (Session.
    # _add_facts) insert these into the graph in this exact sequence, and nodes
    # sharing the same rule.order execute in insertion order, so reordering
    # here silently changes which fact-combination a rule processes first
    # among tied-priority matches.
    include_only_set = set(include_only)
    result: list[list] = []
    _append_matching(ll, 0, [], False, include_only_set, result)
    return result

def _append_matching(ll: list, i: int, prefix: list, satisfied: bool, include_only: set, result: list[list]) -> None:
    # `prefix` holds the elements chosen for positions 0..i-1. `satisfied` is
    # True once one of those elements is in include_only - at that point every
    # way of completing `prefix` qualifies, so there's nothing left to filter:
    # hand off to _append_all to enumerate the remaining positions unconditionally
    # (cheaper, and avoids pointless `in include_only` checks on the rest of the tuple).
    if satisfied:
        _append_all(ll, i, prefix, result)
        return
    if i == len(ll):
        # Reached the end of a full-length prefix that never hit an include_only
        # element - this combination doesn't qualify. Just return without
        # appending; this is the branch that replaces the "filter out" half of
        # generate-then-filter.
        return
    for x in ll[i]:
        # One recursive call per choice of x for position i, trying them in
        # ll[i]'s own order (matching cartesian()'s nesting). `satisfied` for the
        # recursive call is just "does x itself qualify" - OR'd in implicitly,
        # since the only way to become satisfied is for the current or an
        # earlier position to be an include_only element.
        _append_matching(ll, i + 1, prefix + [x], x in include_only, include_only, result)

def _append_all(ll: list, i: int, prefix: list, result: list[list]) -> None:
    # Unfiltered cartesian continuation from position i onward: every leaf is
    # appended to result. Structurally identical to cartesian() below, just
    # resuming from a partially-built prefix instead of starting from [].
    if i == len(ll):
        result.append(prefix)
        return
    for x in ll[i]:
        _append_all(ll, i + 1, prefix + [x], result)

def cartesian(ll: list) -> list[list]:
    # Plain cartesian product - used as-is when there's no include_only filter,
    # and as the reference definition that _append_matching/_append_all's
    # order and contents are checked against.
    result: list[list] = [[]]
    for l in ll:
        result = [x + [y] for x in result for y in l]
    return result
