from hashlib import sha256

from andes_context_os.producers.authorized_context import (
    AuthorizedContextManifest,
    AuthorizedContextProducer,
    ContextProductionStatus,
    ResolvedContextSource,
)

CONTEXT = {
    "contract_version": "0.1",
    "context_id": "example-context",
    "kind": "repository",
    "title": "Example repository capability",
    "reference": "example:repository",
    "summary": "Fictitious repository capability.",
    "domains": ["logistics"],
    "activities": ["access"],
    "territory_refs": [],
    "tags": ["example"],
    "sensitivity": "public",
    "reviewed_at": "2026-08-30T10:00:00-03:00",
    "limitations": ["Fictitious example only."],
}


def manifest_entry(**overrides):
    payload = {
        "entry_id": "entry-example",
        "resolver_id": "fixture",
        "source_locator": "example://source",
        "context": CONTEXT,
    }
    payload.update(overrides)
    return payload


def manifest_with(*entries):
    return AuthorizedContextManifest.from_dict(
        {"manifest_version": "0.1", "entries": list(entries)}
    )


class RecordingResolver:
    def __init__(self, resolved):
        self.resolved = resolved
        self.calls = []

    def resolve(self, locator):
        self.calls.append(locator)
        return self.resolved


def test_unpinned_success_emits_unchanged_record_and_exact_hash_receipt():
    content = b"line-1\r\nline-2\n"
    resolver = RecordingResolver(ResolvedContextSource("example-source:v1", content))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": resolver},
    )
    assert production.status is ContextProductionStatus.COMPLETE
    assert production.catalog.records[0].to_dict() == CONTEXT
    assert resolver.calls == ["example://source"]
    assert production.receipts[0].source_content_sha256 == sha256(content).hexdigest()
    assert production.receipts[0].source_identity == "example-source:v1"
    assert production.failures == ()


def test_exact_bytes_are_not_normalized():
    producer = AuthorizedContextProducer()
    first = producer.produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("same:v1", b"x\n"))},
    )
    second = producer.produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("same:v1", b"x\r\n"))},
    )
    assert first.receipts[0].source_content_sha256 != second.receipts[0].source_content_sha256


def test_empty_bytes_are_valid():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("empty:v1", b""))},
    )
    assert production.receipts[0].source_content_sha256 == sha256(b"").hexdigest()


def test_mapping_key_selects_exact_resolver():
    first = RecordingResolver(ResolvedContextSource("wrong", b"wrong"))
    second = RecordingResolver(ResolvedContextSource("right", b"right"))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(resolver_id="second")),
        {"first": first, "second": second},
    )
    assert first.calls == []
    assert second.calls == ["example://source"]
    assert production.receipts[0].resolver_id == "second"


def test_identity_pin_success():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_source_identity="source:v1")),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", b"payload"))},
    )
    assert production.status is ContextProductionStatus.COMPLETE


def test_content_pin_success():
    content = b"payload"
    production = AuthorizedContextProducer().produce(
        manifest_with(
            manifest_entry(expected_content_sha256=sha256(content).hexdigest())
        ),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", content))},
    )
    assert production.status is ContextProductionStatus.COMPLETE
