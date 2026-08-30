from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from andes_context_os.common import REGISTRY_VERSION, require_aware_iso8601, require_fields, require_text
from andes_context_os.hashing import sha256_json
from andes_context_os.sources import SourceRecord


@dataclass(frozen=True, slots=True)
class SourceRegistry:
    registry_version: str
    generated_at: str | None
    sources: tuple[SourceRecord, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRegistry":
        required = {"registry_version", "sources"}
        allowed = required | {"generated_at"}
        require_fields(payload, required=required, allowed=allowed)

        registry_version = require_text(payload["registry_version"], "registry_version")
        if registry_version != REGISTRY_VERSION:
            raise ValueError(f"registry_version must be {REGISTRY_VERSION}")

        generated_at_value = payload.get("generated_at")
        generated_at = (
            require_aware_iso8601(generated_at_value, "generated_at")
            if generated_at_value is not None
            else None
        )

        raw_sources = payload["sources"]
        if not isinstance(raw_sources, list):
            raise ValueError("sources must be a list")

        parsed_sources: list[SourceRecord] = []
        seen_ids: set[str] = set()
        for raw_source in raw_sources:
            if not isinstance(raw_source, dict):
                raise ValueError("each source must be an object")
            source = SourceRecord.from_dict(raw_source)
            if source.source_id in seen_ids:
                raise ValueError(f"duplicate source_id: {source.source_id}")
            seen_ids.add(source.source_id)
            parsed_sources.append(source)

        return cls(
            registry_version=registry_version,
            generated_at=generated_at,
            sources=tuple(parsed_sources),
        )

    @classmethod
    def load(cls, path: str | Path) -> "SourceRegistry":
        registry_path = Path(path)
        try:
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid registry JSON: {registry_path}") from exc
        if not isinstance(payload, dict):
            raise ValueError("registry root must be an object")
        return cls.from_dict(payload)

    @property
    def registry_hash(self) -> str:
        canonical_payload = {
            "registry_version": self.registry_version,
            "sources": [
                source.to_dict()
                for source in sorted(self.sources, key=lambda item: item.source_id)
            ],
        }
        return sha256_json(canonical_payload)

    def get(self, source_id: str) -> SourceRecord:
        source_id = require_text(source_id, "source_id")
        for source in self.sources:
            if source.source_id == source_id:
                return source
        raise KeyError(source_id)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "registry_version": self.registry_version,
            "sources": [source.to_dict() for source in self.sources],
        }
        if self.generated_at is not None:
            payload["generated_at"] = self.generated_at
        return payload
