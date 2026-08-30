from copy import deepcopy
import json

import pytest

from andes_context_os.internal_context import (
    ContextSensitivity,
    InternalContextCatalog,
    InternalContextKind,
    InternalContextRecord,
)

VALID_RECORD = {
    "contract_version": "0.1",
    "context_id": "repo-geoplatform-access",
    "kind": "repository",
    "title": "GeoPlatform access capability",
    "reference": "repo:GeoPlatform#access",
    "summary": "Existing territorial access capability worth inspecting before a new spike.",
    "domains": ["logistics"],
    "activities": ["access", "route_planning"],
    "territory_refs": [],
    "tags": ["geospatial", "access"],
    "sensitivity": "public",
    "reviewed_at": "2026-08-30T09:00:00-03:00",
    "limitations": ["Reference does not establish current road condition"],
}


def test_record_round_trips():
    record = InternalContextRecord.from_dict(VALID_RECORD)
    assert record.to_dict() == VALID_RECORD
    assert record.kind is InternalContextKind.REPOSITORY
    assert record.sensitivity is ContextSensitivity.PUBLIC


@pytest.mark.parametrize("field", ["password", "api_key", "access_token", "cookie"])
def test_record_rejects_unknown_secret_like_fields(field):
    with pytest.raises(ValueError, match=f"unknown fields: {field}"):
        InternalContextRecord.from_dict({**VALID_RECORD, field: "secret"})


def test_record_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        InternalContextRecord.from_dict({**VALID_RECORD, "kind": "memory_blob"})


def test_record_rejects_unknown_domain():
    with pytest.raises(ValueError, match="domains"):
        InternalContextRecord.from_dict({**VALID_RECORD, "domains": ["magic"]})


def test_record_rejects_unknown_activity():
    with pytest.raises(ValueError, match="activities"):
        InternalContextRecord.from_dict({**VALID_RECORD, "activities": ["teleportation"]})


def test_record_rejects_naive_reviewed_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        InternalContextRecord.from_dict({**VALID_RECORD, "reviewed_at": "2026-08-30T09:00:00"})


VALID_CATALOG = {"catalog_version": "0.1", "records": [VALID_RECORD]}


def test_catalog_round_trips():
    assert InternalContextCatalog.from_dict(VALID_CATALOG).to_dict() == VALID_CATALOG


def test_catalog_rejects_duplicate_context_ids():
    payload = {"catalog_version": "0.1", "records": [VALID_RECORD, deepcopy(VALID_RECORD)]}
    with pytest.raises(ValueError, match="duplicate context_id"):
        InternalContextCatalog.from_dict(payload)


def test_catalog_rejects_non_object_record():
    with pytest.raises(ValueError, match="each record must be an object"):
        InternalContextCatalog.from_dict({"catalog_version": "0.1", "records": ["secret-text"]})


def test_catalog_loads_local_json(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(VALID_CATALOG), encoding="utf-8")
    assert InternalContextCatalog.load(path).records[0].context_id == VALID_RECORD["context_id"]


def test_catalog_load_rejects_malformed_json_without_echoing_contents(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"secret-summary": ', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid internal context catalog JSON") as exc:
        InternalContextCatalog.load(path)
    assert "secret-summary" not in str(exc.value)
