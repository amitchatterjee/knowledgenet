
def permutations(hier_list):
    perms = [[]]
    for child in hier_list:
        perms = __append(perms, child)
    return perms

def __append(parent, child):
    ret = []
    for p in parent:
        for e in child:
            ret.append(p+[e])
    return ret