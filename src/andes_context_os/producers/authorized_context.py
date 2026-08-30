from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping, Protocol

from andes_context_os.common import require_fields, require_text
from andes_context_os.internal_context import (
    CATALOG_VERSION,
    InternalContextCatalog,
    InternalContextRecord,
)

MANIFEST_VERSION = "0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_exact_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field} must not contain surrounding whitespace")
    return value


def _optional_exact_text(value: Any, field: str) -> str | None:
    return None if value is None else _require_exact_text(value, field)


def _optional_sha256(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = _require_exact_text(value, field)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field} must be 64 lowercase hex characters")
    return text


@dataclass(frozen=True, slots=True)
class AuthorizedContextManifestEntry:
    entry_id: str
    resolver_id: str
    source_locator: str
    expected_source_identity: str | None
    expected_content_sha256: str | None
    context: InternalContextRecord

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AuthorizedContextManifestEntry":
        required = {"entry_id", "resolver_id", "source_locator", "context"}
        allowed = required | {"expected_source_identity", "expected_content_sha256"}
        require_fields(payload, required=required, allowed=allowed)
        raw_context = payload["context"]
        if not isinstance(raw_context, dict):
            raise ValueError("context must be an object")
        return cls(
            entry_id=require_text(payload["entry_id"], "entry_id"),
            resolver_id=require_text(payload["resolver_id"], "resolver_id"),
            source_locator=_require_exact_text(payload["source_locator"], "source_locator"),
            expected_source_identity=_optional_exact_text(
                payload.get("expected_source_identity"),
                "expected_source_identity",
            ),
            expected_content_sha256=_optional_sha256(
                payload.get("expected_content_sha256"),
                "expected_content_sha256",
            ),
            context=InternalContextRecord.from_dict(raw_context),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "entry_id": self.entry_id,
            "resolver_id": self.resolver_id,
            "source_locator": self.source_locator,
            "context": self.context.to_dict(),
        }
        if self.expected_source_identity is not None:
            payload["expected_source_identity"] = self.expected_source_identity
        if self.expected_content_sha256 is not None:
            payload["expected_content_sha256"] = self.expected_content_sha256
        return payload


@dataclass(frozen=True, slots=True)
class AuthorizedContextManifest:
    manifest_version: str
    entries: tuple[AuthorizedContextManifestEntry, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AuthorizedContextManifest":
        fields = {"manifest_version", "entries"}
        require_fields(payload, required=fields, allowed=fields)
        version = require_text(payload["manifest_version"], "manifest_version")
        if version != MANIFEST_VERSION:
            raise ValueError(f"manifest_version must be {MANIFEST_VERSION}")
        raw_entries = payload["entries"]
        if not isinstance(raw_entries, list):
            raise ValueError("entries must be a list")
        parsed: list[AuthorizedContextManifestEntry] = []
        for raw in raw_entries:
            if not isinstance(raw, dict):
                raise ValueError("each manifest entry must be an object")
            parsed.append(AuthorizedContextManifestEntry.from_dict(raw))
        entry_ids = [item.entry_id for item in parsed]
        context_ids = [item.context.context_id for item in parsed]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("duplicate entry_id in authorized context manifest")
        if len(context_ids) != len(set(context_ids)):
            raise ValueError("duplicate context_id in authorized context manifest")
        return cls(
            manifest_version=version,
            entries=tuple(
                sorted(parsed, key=lambda item: (item.context.context_id, item.entry_id))
            ),
        )

    @classmethod
    def load(cls, path: str | Path) -> "AuthorizedContextManifest":
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("invalid authorized context manifest JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("authorized context manifest root must be an object")
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "entries": [item.to_dict() for item in self.entries],
        }


class ContextProductionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ContextProductionFailureReason(StrEnum):
    RESOLVER_NOT_REGISTERED = "resolver_not_registered"
    RESOLUTION_FAILED = "resolution_failed"
    SOURCE_IDENTITY_MISMATCH = "source_identity_mismatch"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    INVALID_RESOLVED_SOURCE = "invalid_resolved_source"


@dataclass(frozen=True, slots=True)
class ResolvedContextSource:
    source_identity: str
    content: bytes


class ExactContentResolver(Protocol):
    def resolve(self, locator: str) -> ResolvedContextSource:
        ...


@dataclass(frozen=True, slots=True)
class ContextSourceReceipt:
    entry_id: str
    context_id: str
    resolver_id: str
    source_identity: str
    source_content_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "context_id": self.context_id,
            "resolver_id": self.resolver_id,
            "source_identity": self.source_identity,
            "source_content_sha256": self.source_content_sha256,
        }


@dataclass(frozen=True, slots=True)
class ContextProductionFailure:
    entry_id: str
    context_id: str
    reason: ContextProductionFailureReason

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "context_id": self.context_id,
            "reason": self.reason.value,
        }


@dataclass(frozen=True, slots=True)
class AuthorizedContextProduction:
    manifest_version: str
    status: ContextProductionStatus
    catalog: InternalContextCatalog
    receipts: tuple[ContextSourceReceipt, ...]
    failures: tuple[ContextProductionFailure, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "status": self.status.value,
            "catalog": self.catalog.to_dict(),
            "receipts": [item.to_dict() for item in self.receipts],
            "failures": [item.to_dict() for item in self.failures],
        }


def _failure(
    entry: AuthorizedContextManifestEntry,
    reason: ContextProductionFailureReason,
) -> ContextProductionFailure:
    return ContextProductionFailure(
        entry_id=entry.entry_id,
        context_id=entry.context.context_id,
        reason=reason,
    )


class AuthorizedContextProducer:
    def produce(
        self,
        manifest: AuthorizedContextManifest,
        resolvers: Mapping[str, ExactContentResolver],
    ) -> AuthorizedContextProduction:
        records: list[InternalContextRecord] = []
        receipts: list[ContextSourceReceipt] = []
        failures: list[ContextProductionFailure] = []

        for entry in manifest.entries:
            if entry.resolver_id not in resolvers:
                failures.append(
                    _failure(
                        entry,
                        ContextProductionFailureReason.RESOLVER_NOT_REGISTERED,
                    )
                )
                continue

            resolver = resolvers[entry.resolver_id]
            try:
                resolved = resolver.resolve(entry.source_locator)
            except Exception:
                failures.append(
                    _failure(entry, ContextProductionFailureReason.RESOLUTION_FAILED)
                )
                continue

            if not isinstance(resolved, ResolvedContextSource):
                failures.append(
                    _failure(entry, ContextProductionFailureReason.INVALID_RESOLVED_SOURCE)
                )
                continue

            try:
                source_identity = _require_exact_text(
                    resolved.source_identity,
                    "source_identity",
                )
            except ValueError:
                failures.append(
                    _failure(entry, ContextProductionFailureReason.INVALID_RESOLVED_SOURCE)
                )
                continue

            if not isinstance(resolved.content, bytes):
                failures.append(
                    _failure(entry, ContextProductionFailureReason.INVALID_RESOLVED_SOURCE)
                )
                continue

            if (
                entry.expected_source_identity is not None
                and source_identity != entry.expected_source_identity
            ):
                failures.append(
                    _failure(entry, ContextProductionFailureReason.SOURCE_IDENTITY_MISMATCH)
                )
                continue

            actual_hash = sha256(resolved.content).hexdigest()
            if (
                entry.expected_content_sha256 is not None
                and actual_hash != entry.expected_content_sha256
            ):
                failures.append(
                    _failure(entry, ContextProductionFailureReason.CONTENT_HASH_MISMATCH)
                )
                continue

            records.append(entry.context)
            receipts.append(
                ContextSourceReceipt(
                    entry_id=entry.entry_id,
                    context_id=entry.context.context_id,
                    resolver_id=entry.resolver_id,
                    source_identity=source_identity,
                    source_content_sha256=actual_hash,
                )
            )

        catalog = InternalContextCatalog(
            catalog_version=CATALOG_VERSION,
            records=tuple(sorted(records, key=lambda item: item.context_id)),
        )
        if not manifest.entries or len(records) == len(manifest.entries):
            status = ContextProductionStatus.COMPLETE
        elif records:
            status = ContextProductionStatus.PARTIAL
        else:
            status = ContextProductionStatus.FAILED

        return AuthorizedContextProduction(
            manifest_version=manifest.manifest_version,
            status=status,
            catalog=catalog,
            receipts=tuple(sorted(receipts, key=lambda item: (item.context_id, item.entry_id))),
            failures=tuple(
                sorted(
                    failures,
                    key=lambda item: (item.context_id, item.entry_id, item.reason.value),
                )
            ),
        )
