from typing import List, Any, Iterable


def range_(start, end, step=1):
    """
    Custom range function that includes the end value in the range.
    """
    current_value = start
    while current_value <= end:
        yield current_value
        current_value += step


def list_to_str(given_list: Iterable[int]) -> str:
    return ",".join(map(str, given_list))


def replace_key(given_dict: dict, chosen_value: Any, new_key: Any):
    for key, value in given_dict.copy().items():
        if value == chosen_value:
            # Replace the old key with the new key
            given_dict[new_key] = given_dict.pop(key)


# If any number is missing from a sequence of numbers, then we get that next missing number
def next_number(iterable: Iterable[int], start_from=None):
    starting_number = 0

    if start_from is not None:
        starting_number = start_from

    if not iterable:
        return starting_number

    for num in range_(starting_number, max(iterable)):
        if num not in iterable:
            return num

    return max(iterable) + 1
