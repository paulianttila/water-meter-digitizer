def fill_value_with_leading_zeros(length: int, value: str) -> str:
    """
    Fills the given value with leading zeros to match the specified length.

    Args:
        length (int): The desired length of the resulting string.
        value (str): The value to be filled with leading zeros.

    Returns:
        str: The value with leading zeros, if the length of the value is less than
             the specified length.
             Otherwise, returns the original value.

    """
    return value.zfill(length) if len(value) < length else value


def fill_value_with_ending_zeros(length: int, value: str) -> str:
    """
    Fills the given value with ending zeros until it reaches the specified length.

    Args:
        length (int): The desired length of the value.
        value (str): The value to be filled with ending zeros.

    Returns:
        str: The value filled with ending zeros.

    """
    if value.startswith("-"):
        length += 1

    while len(value) < length:
        value = f"{value}0"
    return value


def fill_with_predecessor_digits(value: str, predecessor: str) -> str:
    """
    Fills the given value with digits from the predecessor string.

    Args:
        value (str): The value to be filled with digits.
        predecessor (str): The string containing the predecessor digits.

    Returns:
        str: The new value with filled digits.

    Example:
        >>> fill_with_predecessor_digits("1N3N", "1234")
        '1234'
    """
    if len(value) != len(predecessor):
        return value
    newVal = ""
    for i in range(len(value) - 1, -1, -1):
        v = predecessor[i] if value[i] == "N" else value[i]
        newVal = f"{v}{newVal}"
    return newVal


def str2bool(val):
    """
    Converts a string representation of a boolean value to its corresponding boolean
    value.

    Args:
        val (str): The string representation of the boolean value.

    Returns:
        bool: The boolean value corresponding to the input string.

    Examples:
        >>> str2bool("true")
        True
        >>> str2bool("false")
        False
        >>> str2bool("yes")
        True
        >>> str2bool("no")
        False
        >>> str2bool("1")
        True
        >>> str2bool("0")
        False
    """
    return val.lower() in ("yes", "true", "1")
