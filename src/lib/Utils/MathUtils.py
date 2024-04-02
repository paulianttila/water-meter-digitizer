def fill_value_with_leading_zeros(length: int, value: str) -> str:
    return value.zfill(length) if len(value) < length else value


def fill_value_with_ending_zeros(length: int, value: str) -> str:
    while len(value) < length:
        value = f"{value}0"
    return value


def fill_with_predecessor_digits(value: str, predecessor: str) -> str:
    newVal = ""
    for i in range(len(value) - 1, -1, -1):
        v = predecessor[i] if value[i] == "N" else value[i]
        newVal = f"{v}{newVal}"
    return newVal


def str2bool(val):
    return val.lower() in ("yes", "true", "1")
