def combinations(ll: list, include_only: list | None = None) -> list[list]:
    if include_only is None:
        include_only = []
    # TODO: Look into optimizing this. Instead of creating all combinations and then excluding, is there a better way to do this?
    all_perms = cartesian(ll)

    included_perms: list[list] = []
    if len(include_only):
        for perm in all_perms:
            overlap = [x for x in perm if x in include_only]
            if len(overlap):
                included_perms.append(perm)
    else:
        included_perms = all_perms
    return included_perms

def cartesian(ll: list) -> list[list]:
    result: list[list] = [[]]
    for l in ll:
        result = [x + [y] for x in result for y in l]
    return result
