import string
import unicodedata

import pytest

from gitmentario.helpers import safe_name


def test_basic_valid_name():
    assert safe_name("valid_name-123") == "valid_name-123"


def test_unicode_normalization():
    # é becomes e, ä becomes a
    assert safe_name("café_ä") == "cafe_a"


def test_forbidden_chars_removed():
    # Characters like < > : " / \ | ? * are removed
    cleaned = safe_name('inva<lid>:na"me/\\|?*')
    assert cleaned == "invalidname"

    cleaned == safe_name("invalid<strong>name</strong>")
    assert cleaned == "invalidname"


def test_spaces_replaced_by_underscore():
    assert safe_name("this is a test") == "this_is_a_test"


def test_trailing_dots_and_spaces_stripped():
    assert safe_name("filename.   ") == "filename"
    assert safe_name("  .filename") == "filename"


def test_empty_after_cleanup_raises():
    with pytest.raises(ValueError):
        safe_name("<<::>>")


def test_allowable_chars_left_intact():
    allowed = "-_.()ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    assert safe_name(allowed) == allowed
