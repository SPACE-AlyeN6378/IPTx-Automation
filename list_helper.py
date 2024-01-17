def range_(start, end, step=1):
    """
    Custom range function that includes the end value in the range.
    """
    current_value = start
    while current_value <= end:
        yield current_value
        current_value += step
