import pytest

from app.services.isbn import is_valid_isbn, normalize_isbn


def test_normalize_strips_hyphens():
    assert normalize_isbn("978-0-13-468599-1") == "9780134685991"


def test_normalize_strips_spaces():
    assert normalize_isbn("978 0 13 468599 1") == "9780134685991"


def test_normalize_isbn13_passthrough():
    assert normalize_isbn("9780134685991") == "9780134685991"


def test_normalize_isbn10_to_isbn13():
    assert normalize_isbn("0-8044-2957-X") == "9780804429573"


def test_normalize_isbn10_numeric_check_digit():
    assert normalize_isbn("0134685997") == "9780134685991"


def test_normalize_isbn10_lowercase_check_digit():
    assert normalize_isbn("080442957x") == "9780804429573"


def test_normalize_invalid_check_digit_raises():
    with pytest.raises(ValueError):
        normalize_isbn("978-0-13-468599-2")


def test_normalize_garbage_raises():
    with pytest.raises(ValueError):
        normalize_isbn("not-an-isbn")


def test_normalize_asin_raises():
    with pytest.raises(ValueError):
        normalize_isbn("B00005N5PF")


def test_is_valid_true_for_valid_isbn13():
    assert is_valid_isbn("978-0-13-468599-1") is True


def test_is_valid_true_for_valid_isbn10():
    assert is_valid_isbn("0-8044-2957-X") is True


def test_is_valid_false_for_invalid_check_digit():
    assert is_valid_isbn("978-0-13-468599-2") is False


def test_is_valid_false_for_asin():
    assert is_valid_isbn("B00005N5PF") is False
