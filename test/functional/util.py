def find_result_of_type(cls, results):
    return [result for result in results if result.__class__ == cls]