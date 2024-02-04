from typing import Iterable

# *** CUSTOM EXCEPTIONS ***
class NetworkError(Exception):
    def __init__(self, message="There's something wrong with your network"):
        self.message = message
        super().__init__(self.message)


class SwitchportError(Exception):
    def __init__(self, message="There's something wrong with the switchport"):
        self.message = message
        super().__init__(self.message)


class NotFoundError(Exception):
    def __init__(self, message="Not found"):
        self.message = message
        super().__init__(self.message)


# Custom range function that includes the end value in the range.
def range_(start, end, step=1):
    current_value = start
    while current_value <= end:
        yield current_value
        current_value += step


# Getting the missing number
def next_number(iterable: Iterable[int], starting_number=0):
    # If the list is empty, you return the starting number
    if not iterable:
        return starting_number

    # Looks for the first of all missing numbers
    for num in range_(starting_number, max(iterable)):
        # Looks for the first of all missing numbers
        if num not in iterable:
            return num
    # Otherwise, return the missing number
    return max(iterable) + 1
