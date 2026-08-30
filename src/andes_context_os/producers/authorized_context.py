from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from andes_context_os.common import require_fields, require_text
from andes_context_os.internal_context import InternalContextRecord

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
