from src.Utils.MathUtils import (
    fill_value_with_leading_zeros,
    fill_value_with_ending_zeros,
    fill_with_predecessor_digits,
)


def test_fill_value_with_leading_zeros():
    # Test case 1: Value length is less than the desired length
    assert fill_value_with_leading_zeros(5, "123") == "00123"

    # Test case 2: Value length is equal to the desired length
    assert fill_value_with_leading_zeros(3, "456") == "456"

    # Test case 3: Value length is greater than the desired length
    assert fill_value_with_leading_zeros(4, "7890") == "7890"

    # Test case 4: Value length is zero
    assert fill_value_with_leading_zeros(6, "") == "000000"

    # Test case 5: Value length is negative
    assert fill_value_with_leading_zeros(8, "-12") == "-0000012"


def test_fill_value_with_ending_zeros():
    # Test case 1: Value length is less than the desired length
    assert fill_value_with_ending_zeros(5, "123") == "12300"

    # Test case 2: Value length is equal to the desired length
    assert fill_value_with_ending_zeros(3, "456") == "456"

    # Test case 3: Value length is greater than the desired length
    assert fill_value_with_ending_zeros(4, "7890") == "7890"

    # Test case 4: Value length is zero
    assert fill_value_with_ending_zeros(6, "") == "000000"

    # Test case 5: Value length is negative
    assert fill_value_with_ending_zeros(8, "-12") == "-12000000"


def test_fill_with_predecessor_digits():
    # Test case 1: Value contains "N" and predecessor has enough digits
    assert fill_with_predecessor_digits("1N3N", "1234") == "1234"

    # Test case 2: Value contains "N" and predecessor has fewer digits
    assert fill_with_predecessor_digits("1N3N", "12") == "1N3N"

    # Test case 3: Value does not contain "N"
    assert fill_with_predecessor_digits("1234", "5678") == "1234"

    # Test case 4: Value is empty
    assert fill_with_predecessor_digits("", "1234") == ""

    # Test case 5: Predecessor is empty
    assert fill_with_predecessor_digits("1N3N", "") == "1N3N"
