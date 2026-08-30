from hashlib import sha256

import pytest

from andes_context_os.producers.authorized_context import (
    AuthorizedContextManifest,
    AuthorizedContextProducer,
    ContextProductionFailureReason,
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


class RaisingResolver:
    def resolve(self, locator):
        raise RuntimeError(f"private locator={locator} token=never-serialize")


class WrongReturnResolver:
    def resolve(self, locator):
        return {"source_identity": "not-contract", "content": b"x"}


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


@pytest.mark.parametrize(
    ("resolvers", "entry", "reason"),
    [
        ({}, manifest_entry(), ContextProductionFailureReason.RESOLVER_NOT_REGISTERED),
        ({"fixture": RaisingResolver()}, manifest_entry(), ContextProductionFailureReason.RESOLUTION_FAILED),
        ({"fixture": WrongReturnResolver()}, manifest_entry(), ContextProductionFailureReason.INVALID_RESOLVED_SOURCE),
    ],
)
def test_failed_entry_has_no_record_or_receipt(resolvers, entry, reason):
    production = AuthorizedContextProducer().produce(manifest_with(entry), resolvers)
    assert production.status is ContextProductionStatus.FAILED
    assert production.catalog.records == ()
    assert production.receipts == ()
    assert production.failures[0].reason is reason


def test_identity_mismatch_fails_closed():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_source_identity="approved:v1")),
        {"fixture": RecordingResolver(ResolvedContextSource("actual:v2", b"payload"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.SOURCE_IDENTITY_MISMATCH
    assert production.catalog.records == ()


def test_hash_mismatch_fails_closed():
    production = AuthorizedContextProducer().produce(
        manifest_with(
            manifest_entry(expected_content_sha256=sha256(b"approved").hexdigest())
        ),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", b"changed"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.CONTENT_HASH_MISMATCH
    assert production.catalog.records == ()


def test_resolved_identity_with_surrounding_whitespace_is_invalid():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource(" source:v1 ", b"payload"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.INVALID_RESOLVED_SOURCE


def test_non_bytes_content_is_invalid_even_if_type_hint_is_ignored_at_runtime():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", "not-bytes"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.INVALID_RESOLVED_SOURCE


def test_failure_serialization_does_not_leak_locator_or_exception_text():
    locator = "private://vault/secret-note"
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(source_locator=locator)),
        {"fixture": RaisingResolver()},
    )
    text = repr(production.to_dict())
    assert locator not in text
    assert "never-serialize" not in text
    assert "private locator" not in text


def test_partial_keeps_only_successful_independent_entry():
    ok_context = {**CONTEXT, "context_id": "a-ok", "reference": "example:a-ok"}
    good = manifest_entry(
        entry_id="entry-ok",
        source_locator="example://ok",
        context=ok_context,
    )
    bad = manifest_entry(entry_id="entry-bad", resolver_id="missing")
    production = AuthorizedContextProducer().produce(
        manifest_with(bad, good),
        {"fixture": RecordingResolver(ResolvedContextSource("ok:v1", b"ok"))},
    )
    assert production.status is ContextProductionStatus.PARTIAL
    assert [item.context_id for item in production.catalog.records] == ["a-ok"]
    assert [item.context_id for item in production.receipts] == ["a-ok"]
    assert [item.context_id for item in production.failures] == ["example-context"]


def test_empty_manifest_is_complete_and_empty():
    production = AuthorizedContextProducer().produce(manifest_with(), {})
    assert production.status is ContextProductionStatus.COMPLETE
    assert production.catalog.records == ()
    assert production.receipts == ()
    assert production.failures == ()


def test_manifest_order_does_not_change_production():
    context_a = {**CONTEXT, "context_id": "a", "reference": "example:a"}
    context_b = {**CONTEXT, "context_id": "b", "reference": "example:b"}
    a = manifest_entry(entry_id="entry-a", source_locator="example://a", context=context_a)
    b = manifest_entry(entry_id="entry-b", source_locator="example://b", context=context_b)

    class DictResolver:
        def resolve(self, locator):
            return ResolvedContextSource(f"identity:{locator}", locator.encode())

    producer = AuthorizedContextProducer()
    first = producer.produce(manifest_with(b, a), {"fixture": DictResolver()})
    second = producer.produce(manifest_with(a, b), {"fixture": DictResolver()})
    assert first.to_dict() == second.to_dict()


def test_resolver_never_receives_locator_absent_from_manifest():
    resolver = RecordingResolver(ResolvedContextSource("approved:v1", b"approved"))
    AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": resolver},
    )
    assert resolver.calls == ["example://source"]
    assert "example://unauthorized-ninth" not in resolver.calls
