import pytest

from andes_context_os.adapters.internal_context import InternalContextAdapter
from andes_context_os.internal_context import InternalContextCatalog
from andes_context_os.research import ResearchIntent, TerritorialScope

INTENT = {
    "contract_version": "0.1",
    "intent_id": "intent-filo-access-001",
    "question_raw": "¿Qué sabemos ya sobre acceso minero en este corredor?",
    "question_canonical": "¿Qué contexto interno existente conviene revisar antes de investigar acceso minero?",
    "question_profile_ref": "question-radar:profile-001",
    "domain": "logistics",
    "activity": "access",
    "goal": "recover prior internal context before external research",
    "constraints": ["research only"],
    "territory_hint": "San Juan Andes",
    "created_at": "2026-08-30T09:00:00-03:00",
}

SCOPE = {
    "contract_version": "0.1",
    "scope_id": "scope-agua-negra",
    "countries": ["AR"],
    "admin_units": [{"country_code": "AR", "admin_level": "1", "official_code": "J", "name": "San Juan", "source_id": "ar_ign_admin"}],
    "project_refs": [],
    "corridor_refs": ["agua-negra-v1"],
    "segment_refs": [],
    "bbox": None,
    "geometry_ref": None,
    "crs": None,
    "precision": "corridor",
    "relation_basis": "known_route",
    "notes": [],
}


def record(context_id, *, kind="repository", domains=None, activities=None, territory_refs=None, sensitivity="public"):
    return {
        "contract_version": "0.1",
        "context_id": context_id,
        "kind": kind,
        "title": f"Title {context_id}",
        "reference": f"ref:{context_id}",
        "summary": f"Summary {context_id}",
        "domains": ["logistics"] if domains is None else domains,
        "activities": ["access"] if activities is None else activities,
        "territory_refs": [] if territory_refs is None else territory_refs,
        "tags": [],
        "sensitivity": sensitivity,
        "reviewed_at": "2026-08-30T08:00:00-03:00",
        "limitations": [],
    }


def build_snapshot(*records):
    return InternalContextAdapter().snapshot(
        ResearchIntent.from_dict(INTENT),
        TerritorialScope.from_dict(SCOPE),
        InternalContextCatalog.from_dict({"catalog_version": "0.1", "records": list(records)}),
        generated_at="2026-08-30T10:00:00-03:00",
    )


def test_territorial_record_requires_exact_match():
    snapshot = build_snapshot(record("peru-only", territory_refs=["PE"]))
    assert snapshot.related_repositories == ()


def test_exact_corridor_match_preserves_all_reasons():
    snapshot = build_snapshot(record("agua-negra", territory_refs=["agua-negra-v1"]))
    assert [reason.value for reason in snapshot.related_repositories[0].match_reasons] == [
        "activity_match", "domain_match", "territory_match"
    ]


def test_territory_only_record_can_match():
    snapshot = build_snapshot(record("corridor-note", kind="vault_note", domains=[], activities=[], territory_refs=["agua-negra-v1"]))
    assert [reason.value for reason in snapshot.related_vault_notes[0].match_reasons] == ["territory_match"]


def test_restricted_match_is_non_emitting_and_non_leaking():
    secret_id = "restricted-secret-id"
    snapshot = build_snapshot(record(secret_id, kind="known_evidence", territory_refs=["agua-negra-v1"], sensitivity="restricted"))
    text = repr(snapshot.to_dict())
    assert snapshot.known_evidence == ()
    assert snapshot.missing_context == (
        "no internal context matched the current intent and territorial scope",
        "restricted internal context was omitted",
    )
    assert secret_id not in text
    assert f"ref:{secret_id}" not in text
    assert f"Summary {secret_id}" not in text


def test_restricted_message_is_emitted_once():
    snapshot = build_snapshot(
        record("secret-1", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
        record("secret-2", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
    )
    assert snapshot.missing_context.count("restricted internal context was omitted") == 1


def test_catalog_order_does_not_change_snapshot():
    a = record("a-record")
    b = record("b-record")
    assert build_snapshot(b, a).to_dict() == build_snapshot(a, b).to_dict()


def test_output_has_no_scores_or_operational_authorizations():
    text = repr(build_snapshot(record("generic")).to_dict())
    for forbidden in (
        "relevance_score", "confidence_score", "risk_score", "truth_score",
        "safe_to_travel", "road_open", "route_authorized", "community_approved",
    ):
        assert forbidden not in text
