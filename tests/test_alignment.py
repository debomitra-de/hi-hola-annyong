import pytest

from pronunciation.alignment import align_phonemes


def test_perfect_match():
    result = align_phonemes(["a", "b", "c"], ["a", "b", "c"])
    assert result == [("a", "a"), ("b", "b"), ("c", "c")]


def test_substitution():
    result = align_phonemes(["a", "b"], ["a", "c"])
    assert result == [("a", "a"), ("b", "c")]


def test_insertion():
    result = align_phonemes(["a", "b"], ["a", "x", "b"])
    assert result == [("a", "a"), (None, "x"), ("b", "b")]


def test_deletion():
    result = align_phonemes(["a", "x", "b"], ["a", "b"])
    assert result == [("a", "a"), ("x", None), ("b", "b")]


from pronunciation.alignment import calculate_per


def test_per_perfect_match():
    assert calculate_per(["a", "b", "c"], ["a", "b", "c"]) == 0.0


def test_per_substitution():
    assert calculate_per(["a", "b"], ["a", "c"]) == 50.0


def test_per_deletion():
    assert calculate_per(["a", "b"], ["a"]) == 50.0


def test_per_insertion():
    assert calculate_per(["a", "b"], ["a", "x", "b"]) == 50.0


def test_per_empty_reference():
    with pytest.raises(ValueError):
        calculate_per([], ["a"])

