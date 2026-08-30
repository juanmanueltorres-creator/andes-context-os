import json

import pytest

from andes_context_os.producers.authorized_context import (
    AuthorizedContextManifest,
    AuthorizedContextManifestEntry,
)

CONTEXT = {
    "contract_version": "0.1",
    "context_id": "example-access-context",
    "kind": "known_gap",
    "title": "Example access freshness gap",
    "reference": "example:access-gap",
    "summary": "A fictitious gap used to test authorized context production.",
    "domains": ["logistics"],
    "activities": ["access"],
    "territory_refs": ["corridor:example-corridor-v1"],
    "tags": ["example"],
    "sensitivity": "public",
    "reviewed_at": "2026-08-30T10:00:00-03:00",
    "limitations": ["Fictitious example only."],
}


def entry_payload(**overrides):
    payload = {
        "entry_id": "entry-example-access",
        "resolver_id": "fixture",
        "source_locator": "example://context/access-gap",
        "expected_source_identity": "example-source:access-gap:v1",
        "expected_content_sha256": "0" * 64,
        "context": CONTEXT,
    }
    payload.update(overrides)
    return payload


def test_manifest_entry_round_trip_preserves_curated_context():
    entry = AuthorizedContextManifestEntry.from_dict(entry_payload())
    assert entry.context.context_id == "example-access-context"
    assert entry.to_dict() == entry_payload()


def test_manifest_is_canonical_by_context_id_then_entry_id():
    second = {**CONTEXT, "context_id": "a-context", "reference": "example:a"}
    manifest = AuthorizedContextManifest.from_dict({
        "manifest_version": "0.1",
        "entries": [
            entry_payload(),
            entry_payload(
                entry_id="entry-a",
                source_locator="example://a",
                context=second,
            ),
        ],
    })
    assert [item.context.context_id for item in manifest.entries] == [
        "a-context",
        "example-access-context",
    ]
    assert AuthorizedContextManifest.from_dict(manifest.to_dict()) == manifest


def test_manifest_load_reads_local_json(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps({"manifest_version": "0.1", "entries": []}),
        encoding="utf-8",
    )
    assert AuthorizedContextManifest.load(path).entries == ()


def test_duplicate_entry_id_is_rejected():
    with pytest.raises(ValueError, match="duplicate entry_id"):
        AuthorizedContextManifest.from_dict({
            "manifest_version": "0.1",
            "entries": [
                entry_payload(),
                entry_payload(context={**CONTEXT, "context_id": "other"}),
            ],
        })


def test_duplicate_context_id_is_rejected():
    with pytest.raises(ValueError, match="duplicate context_id"):
        AuthorizedContextManifest.from_dict({
            "manifest_version": "0.1",
            "entries": [entry_payload(), entry_payload(entry_id="other-entry")],
        })


def test_unknown_secret_like_field_rejects_without_echoing_value():
    secret = "never-echo-this-token"
    with pytest.raises(ValueError) as exc_info:
        AuthorizedContextManifestEntry.from_dict(entry_payload(access_token=secret))
    assert "access_token" in str(exc_info.value)
    assert secret not in str(exc_info.value)


@pytest.mark.parametrize("field", ["source_locator", "expected_source_identity"])
def test_exact_identity_fields_reject_surrounding_whitespace(field):
    payload = entry_payload(**{field: " exact-value "})
    with pytest.raises(ValueError, match="surrounding whitespace"):
        AuthorizedContextManifestEntry.from_dict(payload)


@pytest.mark.parametrize("bad_hash", ["ABC", "g" * 64, "A" * 64, "0" * 63])
def test_expected_sha256_requires_lowercase_64_hex(bad_hash):
    with pytest.raises(ValueError, match="64 lowercase hex"):
        AuthorizedContextManifestEntry.from_dict(
            entry_payload(expected_content_sha256=bad_hash)
        )


def test_unsupported_manifest_version_is_rejected():
    with pytest.raises(ValueError, match="manifest_version must be 0.1"):
        AuthorizedContextManifest.from_dict(
            {"manifest_version": "9.9", "entries": []}
        )
