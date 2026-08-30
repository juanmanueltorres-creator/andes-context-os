import pytest

from andes_context_os.sources import SourceRecord, SourceRuntimeObservation


VALID_SOURCE = {
    "contract_version": "0.1",
    "source_id": "ar_sanjuan_mining_cadastre",
    "display_name": "Catastro Minero San Juan",
    "provider": "Ministerio de Minería de San Juan",
    "jurisdiction": "AR-J",
    "domains": ["mining", "cadastre"],
    "source_kind": "official",
    "authority": "primary_authority",
    "access": {
        "access_type": "wfs",
        "endpoint_or_reference": "https://catastrominero.sanjuan.gob.ar/geoserver/wfs",
        "requires_auth": False,
        "expected_formats": ["application/json", "gml"],
        "rate_limit_notes": [],
    },
    "coverage": {
        "countries": ["AR"],
        "admin_units": ["AR-J"],
        "bbox": None,
        "coverage_description": "San Juan mining cadastre",
    },
    "temporal_character": "periodic",
    "rights": {
        "license_status": "unknown_review_required",
        "license_name": None,
        "license_reference": None,
        "commercial_reuse": "unknown",
        "redistribution": "unknown",
        "attribution_required": False,
        "legal_review_required": True,
        "rights_notes": ["Verify exact reuse terms before product ingestion"],
    },
    "adapter_binding": {
        "adapter_key": "official_geo_service",
        "adapter_min_version": None,
        "capabilities": ["cadastre_discovery"],
    },
    "declared_status": "candidate",
    "limitations": ["Registry metadata does not prove runtime availability"],
    "references": ["https://catastrominero.sanjuan.gob.ar/geoserver/wfs"],
    "reviewed_at": "2026-08-30T09:00:00-03:00",
    "registry_notes": [],
}


def runtime_payload(status="empty", *, errors=None, notes=None, **overrides):
    payload = {
        "contract_version": "0.1",
        "observation_id": "obs-001",
        "source_id": "ar_sanjuan_mining_cadastre",
        "observed_at": "2026-08-30T09:05:00-03:00",
        "status": status,
        "method": "adapter_query",
        "adapter_key": "official_geo_service",
        "adapter_version": "0.1",
        "response_metadata": {
            "http_status": 200,
            "content_type": "application/json",
            "record_count": 0,
            "elapsed_ms": 52,
        },
        "freshness_observation": None,
        "errors": [] if errors is None else errors,
        "notes": [] if notes is None else notes,
    }
    payload.update(overrides)
    return payload


def test_source_record_accepts_candidate_without_claiming_available():
    source = SourceRecord.from_dict(VALID_SOURCE)
    assert source.declared_status.value == "candidate"


def test_source_record_round_trips():
    assert SourceRecord.from_dict(VALID_SOURCE).to_dict() == VALID_SOURCE


def test_source_record_rejects_available_as_declared_status():
    with pytest.raises(ValueError, match="declared_status"):
        SourceRecord.from_dict({**VALID_SOURCE, "declared_status": "available"})


def test_source_record_rejects_commercial_yes_with_unknown_license():
    payload = {
        **VALID_SOURCE,
        "rights": {**VALID_SOURCE["rights"], "commercial_reuse": "yes"},
    }
    with pytest.raises(ValueError, match="commercial_reuse"):
        SourceRecord.from_dict(payload)


def test_source_record_rejects_secret_like_unknown_key():
    with pytest.raises(ValueError, match="unknown fields: token"):
        SourceRecord.from_dict({**VALID_SOURCE, "token": "abc"})


def test_source_record_rejects_unknown_access_enum():
    payload = {
        **VALID_SOURCE,
        "access": {**VALID_SOURCE["access"], "access_type": "telepathy"},
    }
    with pytest.raises(ValueError, match="access_type"):
        SourceRecord.from_dict(payload)


def test_source_record_rejects_malformed_rights_boolean():
    payload = {
        **VALID_SOURCE,
        "rights": {**VALID_SOURCE["rights"], "legal_review_required": "yes"},
    }
    with pytest.raises(ValueError, match="legal_review_required"):
        SourceRecord.from_dict(payload)


def test_source_record_rejects_unknown_nested_rights_field():
    payload = {
        **VALID_SOURCE,
        "rights": {**VALID_SOURCE["rights"], "api_key": "secret"},
    }
    with pytest.raises(ValueError, match="unknown fields: api_key"):
        SourceRecord.from_dict(payload)


def test_source_record_rejects_naive_reviewed_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        SourceRecord.from_dict({**VALID_SOURCE, "reviewed_at": "2026-08-30T09:00:00"})


@pytest.mark.parametrize("status", ["available", "empty", "partial", "unavailable", "unsupported", "unknown"])
def test_runtime_statuses_are_distinct_and_valid(status):
    observation = SourceRuntimeObservation.from_dict(runtime_payload(status))
    assert observation.status.value == status


def test_runtime_empty_is_not_unavailable():
    observation = SourceRuntimeObservation.from_dict(runtime_payload("empty"))
    assert observation.status.value == "empty"
    assert observation.status.value != "unavailable"


def test_runtime_observation_round_trips():
    payload = runtime_payload("partial", errors=["one layer timed out"])
    assert SourceRuntimeObservation.from_dict(payload).to_dict() == payload


def test_runtime_omitted_requires_explicit_reason():
    with pytest.raises(ValueError, match="explicit reason"):
        SourceRuntimeObservation.from_dict(runtime_payload("omitted"))


def test_runtime_omitted_accepts_note_as_reason():
    observation = SourceRuntimeObservation.from_dict(
        runtime_payload("omitted", notes=["source incompatible with scope"])
    )
    assert observation.status.value == "omitted"


def test_runtime_rejects_naive_observed_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        SourceRuntimeObservation.from_dict(
            runtime_payload(observed_at="2026-08-30T09:05:00")
        )


def test_runtime_rejects_unknown_method():
    with pytest.raises(ValueError, match="method"):
        SourceRuntimeObservation.from_dict(runtime_payload(method="crystal_ball"))


def test_runtime_rejects_unknown_top_level_field():
    with pytest.raises(ValueError, match="unknown fields: road_open"):
        SourceRuntimeObservation.from_dict(runtime_payload(road_open=True))


def test_empty_requires_zero_result_count_when_metadata_is_present():
    payload = runtime_payload(
        "empty",
        response_metadata={
            "http_status": 200,
            "content_type": "application/json",
            "record_count": 3,
            "elapsed_ms": 52,
        },
    )
    with pytest.raises(ValueError, match="record_count=0"):
        SourceRuntimeObservation.from_dict(payload)


def test_response_metadata_rejects_sensitive_header_like_field():
    payload = runtime_payload(
        response_metadata={
            "http_status": 200,
            "content_type": "application/json",
            "record_count": 0,
            "elapsed_ms": 52,
            "authorization": "Bearer secret",
        }
    )
    with pytest.raises(ValueError, match="unknown fields: authorization"):
        SourceRuntimeObservation.from_dict(payload)


def test_source_record_accepts_optional_reviewed_at_omitted():
    payload = {key: value for key, value in VALID_SOURCE.items() if key != "reviewed_at"}
    source = SourceRecord.from_dict(payload)
    assert source.reviewed_at is None


def test_source_rights_accepts_optional_license_fields_omitted():
    rights = {
        key: value
        for key, value in VALID_SOURCE["rights"].items()
        if key not in {"license_name", "license_reference"}
    }
    source = SourceRecord.from_dict({**VALID_SOURCE, "rights": rights})
    assert source.rights.license_name is None
    assert source.rights.license_reference is None


def test_source_coverage_accepts_optional_admin_units_omitted():
    coverage = {
        key: value
        for key, value in VALID_SOURCE["coverage"].items()
        if key != "admin_units"
    }
    source = SourceRecord.from_dict({**VALID_SOURCE, "coverage": coverage})
    assert source.coverage.admin_units == ()


def test_adapter_binding_accepts_optional_min_version_omitted():
    binding = {
        key: value
        for key, value in VALID_SOURCE["adapter_binding"].items()
        if key != "adapter_min_version"
    }
    source = SourceRecord.from_dict({**VALID_SOURCE, "adapter_binding": binding})
    assert source.adapter_binding.adapter_min_version is None
