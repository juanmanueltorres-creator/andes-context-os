import pytest

from andes_context_os.common import require_aware_iso8601, require_fields, require_string_list
from andes_context_os.hashing import sha256_json


def test_require_fields_rejects_unknown_keys():
    with pytest.raises(ValueError, match="unknown fields: token"):
        require_fields({"id": "x", "token": "secret"}, required={"id"}, allowed={"id"})


def test_require_aware_iso8601_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        require_aware_iso8601("2026-08-30T09:00:00", "created_at")


def test_sha256_json_is_order_independent_for_object_keys():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert sha256_json(left) == sha256_json(right)


def test_sha256_json_changes_for_meaningful_change():
    assert sha256_json({"a": 1}) != sha256_json({"a": 2})


def test_require_string_list_rejects_non_list():
    with pytest.raises(ValueError, match="tags must be a list"):
        require_string_list("mining", "tags")


def test_require_string_list_normalizes_strings_to_tuple():
    assert require_string_list([" mining ", "gis"], "tags") == ("mining", "gis")
