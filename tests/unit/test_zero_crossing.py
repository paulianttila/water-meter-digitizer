import math
from typing import Union


def check_digit_consistency(
    current_val: float, decimal_shift: int, is_analog: bool, pre_value: float
) -> float:
    """
    Adjusts `current_val` to ensure digit consistency with `pre_value`,
    accounting for potential zero crossings.

    Parameters:
    - current_val (float): The current reading.
    - decimal_shift (int): The initial decimal shift.
    - is_analog (bool): Indicates if there are analog values involved.
    - pre_value (float): The previous reading.

    Returns:
    - float: Adjusted input value to ensure digit consistency.
    """
    pot = decimal_shift
    # Adjust decimal shift if there are no analog values
    if not is_analog:
        pot += 1

    # Determine maximum position based on the magnitude of the input value
    pot_max = int(math.log10(current_val)) + 1

    while pot <= pot_max:
        # Get current digit before the potential roll-over point
        zw = current_val / (10 ** (pot - 1))
        aktdigit_before = int(zw) % 10

        # Get previous digit before the potential roll-over point
        zw = pre_value / (10 ** (pot - 1))
        olddigit_before = int(zw) % 10

        # Get current digit at the current roll-over point
        zw = current_val / (10**pot)
        aktdigit = int(zw) % 10

        # Get previous digit at the current roll-over point
        zw = pre_value / (10**pot)
        olddigit = int(zw) % 10

        # Check if there has been no zero crossing
        no_zero_crossing = olddigit_before <= aktdigit_before

        if no_zero_crossing:
            # If digits do not match without a zero crossing, synchronize them
            if aktdigit != olddigit:
                current_val += (olddigit - aktdigit) * (10**pot)
        else:
            # If there's a zero crossing but digits are still the same, increment by 1
            if aktdigit == olddigit:
                current_val += 1 * (10**pot)

        # Move to the next position
        pot += 1

    return current_val


def test() -> None:
    result = check_digit_consistency(
        current_val=8.9, decimal_shift=1, is_analog=True, pre_value=7.8
    )

    result = check_digit_consistency(
        current_val=8.9, decimal_shift=1, is_analog=True, pre_value=0.5
    )
    print("Adjusted input:", result)


def determine_actual_value(
    current_digit: float, previous_digit: float
) -> Union[float, int]:
    """
    Determine the correct number based on the previous reading and current reading.
    Adjusts for zero crossing if necessary.

    Parameters:
    - current: float, the current reading from the meter
    - previous: int, the previous number on the meter

    Returns:
    - int, the most likely correct number after applying zero-crossing logic
    """
    # Define threshold for rolling over based on the observed behavior
    lower_threshold = 7.9  # Starting range for potential roll-over
    upper_threshold = 8.1  # Ending range for potential roll-over

    if previous_digit < 8:
        # Case 1: Previous number is less than 8
        if lower_threshold <= current_digit <= upper_threshold:
            # Reading is within the ambiguous threshold, suggesting roll-over
            return previous_digit + 1
        else:
            # No roll-over; round current to the nearest integer
            return int(round(current_digit))
    elif previous_digit >= 8:
        # Case 2: Previous number is 8 or above, nearing a full roll-over to 0
        if current_digit >= 8.9:
            # If the reading is close to 9 or above, assume it’s actually a 0 roll-over
            return 0
        else:
            # No roll-over; round current to the nearest integer
            return int(round(current_digit))
    else:
        # General case (default behavior)
        return int(round(current_digit))


def test2() -> None:
    result = determine_actual_value(current_digit=8.9, previous_digit=9.8)

    print("Adjusted input:", result)
