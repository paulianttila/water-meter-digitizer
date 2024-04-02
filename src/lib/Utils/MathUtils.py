def fillValueWithLeadingZeros(length: int, value: str) -> str:
    return value.zfill(length) if len(value) < length else value


def fillValueWithEndingZeros(length: int, value: str) -> str:
    while len(value) < length:
        value = f"{value}0"
    return value


def fillWithPredecessorDigits(value: str, predecessor: str) -> str:
    newVal = ""
    for i in range(len(value) - 1, -1, -1):
        v = predecessor[i] if value[i] == "N" else value[i]
        newVal = f"{v}{newVal}"
    return newVal


def str2bool(val):
    return val.lower() in ("yes", "true", "1")
