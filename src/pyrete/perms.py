import logging

def permutations(hier_list, include_only=[]):
    perms = [[]]
    for child in hier_list:
        perms = __append(perms, child)
    # logging.debug(f"All permutations:{perms}")
    if len(include_only):
        excludes = []
        for perm in perms:
            overlap = [x for x in perm if x in include_only]
            if not len(overlap):
                excludes.append(perm)
        perms = [x for x in perms if x not in excludes]
        # logging.debug(f"Permutations that includes only {include_only}: {perms}")
    return perms

def __append(parent, child):
    ret = []
    for p in parent:
        for e in child:
            ret.append(p+[e])
    return ret