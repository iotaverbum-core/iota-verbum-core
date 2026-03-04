import math

import pytest

from core.determinism.canonical_json import dumps_canonical


def test_dumps_canonical_ignores_dict_insertion_order():
    left = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
    right = {"nested": {"x": 1, "y": 2}, "a": 1, "b": 2}

    assert dumps_canonical(left) == dumps_canonical(right)


def test_dumps_canonical_normalizes_strings_to_nfc():
    payload = {"text": "Cafe\u0301"}

    assert dumps_canonical(payload) == b'{"text":"Caf\xc3\xa9"}'


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_dumps_canonical_rejects_non_finite_floats(value):
    with pytest.raises(ValueError, match="NaN or Infinity"):
        dumps_canonical({"value": value})
