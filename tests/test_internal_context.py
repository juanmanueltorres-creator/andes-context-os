from copy import deepcopy
import json

import pytest

from andes_context_os.hashing import sha256_json
from andes_context_os.internal_context import (
    ContextSelection,
    ContextSensitivity,
    InternalContextCatalog,
    InternalContextKind,
    InternalContextRecord,
    InternalContextSnapshot,
    MatchReason,
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


VALID_SELECTION = {
    "context_id": "repo-geoplatform-access",
    "kind": "repository",
    "title": "GeoPlatform access capability",
    "reference": "repo:GeoPlatform#access",
    "summary": "Existing territorial access capability worth inspecting before a new spike.",
    "match_reasons": ["activity_match", "domain_match"],
    "limitations": ["Reference does not establish current road condition"],
}


def build_snapshot(*, selections=(VALID_SELECTION,), missing_context=(), generated_at="2026-08-30T10:00:00-03:00"):
    return InternalContextSnapshot.build(
        generated_at=generated_at,
        research_intent_id="intent-filo-access-001",
        question_profile_ref="question-radar:profile-001",
        territorial_scope_id="scope-ar-j",
        selections=tuple(ContextSelection.from_dict(item) for item in selections),
        missing_context=tuple(missing_context),
    )


def test_selection_sorts_reasons_and_rejects_scores():
    payload = {**VALID_SELECTION, "match_reasons": ["domain_match", "activity_match"]}
    selection = ContextSelection.from_dict(payload)
    assert selection.match_reasons == (MatchReason.ACTIVITY_MATCH, MatchReason.DOMAIN_MATCH)
    with pytest.raises(ValueError, match="unknown fields: relevance_score"):
        ContextSelection.from_dict({**VALID_SELECTION, "relevance_score": 0.9})


def test_snapshot_id_is_lowercase_sha256_and_round_trips():
    snapshot = build_snapshot()
    assert len(snapshot.snapshot_id) == 64
    assert set(snapshot.snapshot_id) <= set("0123456789abcdef")
    assert InternalContextSnapshot.from_dict(snapshot.to_dict()).to_dict() == snapshot.to_dict()


def test_snapshot_id_changes_when_content_changes():
    assert build_snapshot(generated_at="2026-08-30T10:00:00-03:00").snapshot_id != build_snapshot(generated_at="2026-08-30T10:01:00-03:00").snapshot_id


def test_snapshot_rejects_tampered_id():
    payload = build_snapshot().to_dict()
    payload["snapshot_id"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot_id mismatch"):
        InternalContextSnapshot.from_dict(payload)


def test_selection_rejects_duplicate_match_reasons():
    payload = {**VALID_SELECTION, "match_reasons": ["domain_match", "domain_match"]}
    with pytest.raises(ValueError, match="duplicate match_reasons"):
        ContextSelection.from_dict(payload)


def test_snapshot_build_rejects_duplicate_context_ids():
    duplicate = ContextSelection.from_dict(VALID_SELECTION)
    with pytest.raises(ValueError, match="duplicate context_id"):
        InternalContextSnapshot.build(
            generated_at="2026-08-30T10:00:00-03:00",
            research_intent_id="intent-filo-access-001",
            question_profile_ref="question-radar:profile-001",
            territorial_scope_id="scope-ar-j",
            selections=(duplicate, duplicate),
            missing_context=(),
        )


def test_snapshot_from_dict_rejects_duplicate_context_ids():
    snapshot = build_snapshot()
    payload = snapshot.to_dict()
    payload["related_repositories"].append(dict(payload["related_repositories"][0]))
    payload["snapshot_id"] = sha256_json({key: value for key, value in payload.items() if key != "snapshot_id"})
    with pytest.raises(ValueError, match="duplicate context_id"):
        InternalContextSnapshot.from_dict(payload)


def test_record_reviewed_at_is_projected_into_snapshot_identity():
    earlier = InternalContextRecord.from_dict(VALID_RECORD)
    later = InternalContextRecord.from_dict(
        {**VALID_RECORD, "reviewed_at": "2026-08-30T11:00:00-03:00"}
    )
    reasons = (MatchReason.ACTIVITY_MATCH, MatchReason.DOMAIN_MATCH)

    earlier_selection = ContextSelection.from_record(earlier, reasons)
    later_selection = ContextSelection.from_record(later, reasons)

    assert earlier_selection.to_dict()["reviewed_at"] == VALID_RECORD["reviewed_at"]
    assert later_selection.to_dict()["reviewed_at"] == "2026-08-30T11:00:00-03:00"

    earlier_snapshot = build_snapshot(selections=(earlier_selection.to_dict(),))
    later_snapshot = build_snapshot(selections=(later_selection.to_dict(),))
    assert earlier_snapshot.snapshot_id != later_snapshot.snapshot_id
