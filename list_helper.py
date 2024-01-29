from typing import List, Any


def range_(start, end, step=1):
    """
    Custom range function that includes the end value in the range.
    """
    current_value = start
    while current_value <= end:
        yield current_value
        current_value += step

def merge_list(given_list: List[Any]):
    new_list = []
    for item in given_list:
        if isinstance(item, list):
            new_list.extend(item)
        else:
            new_list.append(item)
    given_list.clear()
    given_list.extend(new_list)

def list_to_str(given_list: List[int]) -> str:
    return ",".join(str(number) for number in given_list)

def replace_key(given_dict: dict, chosen_value: Any, new_key: Any):
    for key, value in given_dict.copy().items():
        if value == chosen_value:
        # Replace the old key with the new key
            given_dict[new_key] = given_dict.pop(key)
