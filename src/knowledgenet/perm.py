def combinations(ll, include_only=[]):
    # TODO: Look into optimizing this. Instead of creating all combinations and then excluding, is there a better way to do this?
    all_perms = cartesian(ll)
    
    included_perms = []
    if len(include_only):
        for perm in all_perms:
            overlap = [x for x in perm if x in include_only]
            if len(overlap):
                included_perms.append(perm)
    else:
        included_perms = all_perms
    return included_perms

def cartesian(ll: list[list])->list[list]:
    result = [[]]
    for l in ll:
        result = [x + [y] for x in result for y in l]
    return result
