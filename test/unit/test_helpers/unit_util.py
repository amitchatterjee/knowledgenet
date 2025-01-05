from collections import OrderedDict

def find_result_of_type(cls, results):
    return [result for result in results if result.__class__ == cls]

def sort_collectors(matching):
    matching.sort(key=lambda e: e.parent.val)
    result = OrderedDict()
    for each in matching:
        l = list(each.collection)
        l.sort(key=lambda e: e.val)
        l = [i.val for i in l]
        result[each.parent.val] = l
    return result