import itertools

from knowledgenet.core.perm import cartesian, combinations


def _naive_filtered(ll: list, include_only: list) -> list[list]:
    """Independent reference: full cartesian product (via itertools, not this
    package's own cartesian()), filtered to tuples containing >=1 element of
    include_only, preserving the product's natural order. Ground truth for
    what combinations() must reproduce - deliberately not sharing code with
    either the old or new implementation under test.
    """
    include_only_set = set(include_only)
    return [list(perm) for perm in itertools.product(*ll)
            if any(x in include_only_set for x in perm)]


def test_cartesian_basic():
    assert cartesian([[1, 2], [10, 20]]) == [[1, 10], [1, 20], [2, 10], [2, 20]]

def test_cartesian_empty_list_of_lists():
    assert cartesian([]) == [[]]

def test_cartesian_one_empty_inner_list_yields_no_combinations():
    assert cartesian([[1, 2], []]) == []

def test_combinations_no_include_only_returns_full_cartesian():
    ll = [[1, 2], [10, 20]]
    assert combinations(ll) == cartesian(ll)
    assert combinations(ll, None) == cartesian(ll)
    assert combinations(ll, []) == cartesian(ll)

def test_combinations_single_when_clause():
    ll = [[1, 2, 3]]
    assert combinations(ll, [2]) == [[2]]

def test_combinations_new_fact_at_last_position_preserves_order():
    # Hand-derived expected order (matches the pre-optimization generate-
    # then-filter behavior): full cartesian in lexicographic order, rightmost
    # position varying fastest, filtered to tuples containing 2.
    ll = [[1, 2, 3], [1, 2, 3]]
    expected = [[1, 2], [2, 1], [2, 2], [2, 3], [3, 2]]
    assert combinations(ll, [2]) == expected
    assert combinations(ll, [2]) == _naive_filtered(ll, [2])

def test_combinations_empty_ll_with_include_only_yields_nothing():
    assert combinations([], [1, 2]) == []

def test_combinations_no_match_yields_nothing():
    assert combinations([[1, 2], [3, 4]], [99]) == []

def test_combinations_multiple_new_facts():
    ll = [[1, 2, 3], [10, 20, 30]]
    include_only = [2, 10]
    assert combinations(ll, include_only) == _naive_filtered(ll, include_only)

def test_combinations_duplicate_type_across_positions_self_pairing():
    # Same population (e.g. two when-clauses of the same Fact type) at
    # positions 0 and 2. A tuple with the same new fact at both positions is
    # a valid, expected output - nothing excludes self-pairing at this stage.
    claims = [1, 2, 3]
    ll = [claims, [10, 20], claims]
    include_only = [2]
    result = combinations(ll, include_only)
    assert result == _naive_filtered(ll, include_only)
    assert [2, 10, 2] in result
    assert [2, 20, 2] in result

def test_combinations_duplicate_type_new_fact_matches_both_positions_order():
    claims = [1, 2, 3]
    ll = [claims, [10, 20], claims]
    include_only = [2]
    assert combinations(ll, include_only) == _naive_filtered(ll, include_only)

def test_combinations_three_when_clauses_matches_naive_reference():
    ll = [[1, 2], ['a', 'b', 'c'], [100, 200]]
    for include_only in ([1], ['b'], [200], [1, 'b'], ['a', 200]):
        assert combinations(ll, include_only) == _naive_filtered(ll, include_only)
