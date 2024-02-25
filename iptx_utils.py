from typing import Iterable, Tuple, Dict, List
import components.interfaces.interface as inf
import datetime
from colorama import Fore, Style

# CUSTOM TYPES
CommandsDict = Dict[str, List[str]]


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


# Split f0/0 --> (FastEthernet, 0/0) from GNS3 =================================================
def split_port_name(shortname: str = "", longname: str = "") -> Tuple[str, str]:
    # Can't accept both
    if shortname and longname:
        raise TypeError("Which parameter do you expect me to use? Please use any one of these two.")

    required_int_type = ""

    # Short name of format, for e.g. g0/1/0
    if shortname:

        for int_type in inf.Interface.DEFAULT_TYPES:
            if int_type[0].lower() == shortname[0].lower():
                required_int_type = int_type
                break

        if not required_int_type:
            raise ValueError(f"The initial '{shortname[0]}' is of an invalid interface type")

        required_port = shortname[1:]

    # Long name of format, for e.g. GigabitEthernet0/1/0
    elif longname:
        for int_type in inf.Interface.DEFAULT_TYPES:
            if int_type in longname[:len(int_type)]:
                required_int_type = int_type
                break

        if not required_int_type:
            raise ValueError(f"Unacceptable format or invalid interface type '{longname}' - Must be like e.g. "
                             f"GigabitEthernet0/0/1")

        required_port = longname[len(required_int_type):]

    # If the parameters go missing
    else:
        raise TypeError("Argument missing")

    return required_int_type, required_port


# Custom range function that includes the end value in the range.
def range_(start, end, step=1):
    current_value = start
    while current_value <= end:
        yield current_value
        current_value += step


# Getting the missing number
def smallest_missing_non_negative_integer(iterable: Iterable[int], starting_number: int = 0):
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


def print_log(text: str, color_number: int = 2):
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")

    if color_number == 0:
        color = Fore.WHITE + Style.BRIGHT
    elif color_number == 1:
        color = Fore.CYAN + Style.BRIGHT
    else:
        color = Fore.BLUE + Style.BRIGHT

    print(f"{color}{formatted_datetime} | {text}{Style.RESET_ALL}")


def print_warning(text: str):
    print(f"{Fore.YELLOW}WARNING! {text}{Style.RESET_ALL}")


def print_success(text: str):
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    color = Fore.GREEN + Style.BRIGHT

    print(f"{color}{formatted_datetime} | {text}{Style.RESET_ALL}")


def print_table(data):
    # Find the maximum length of each column
    col_width = [max(len(str(item)) for item in col) for col in zip(*data)]

    # Print the table with consistent spacing
    for row in data:
        print(" | ".join("{:{width}}".format(item, width=width) for item, width in zip(row, col_width)))
