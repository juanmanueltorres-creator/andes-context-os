from datetime import datetime
from typing import Any

CONTRACT_VERSION = "0.1"
REGISTRY_VERSION = "0.1"


def require_fields(payload: dict[str, Any], *, required: set[str], allowed: set[str]) -> None:
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    unknown = sorted(payload.keys() - allowed)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(unknown)}")


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def require_aware_iso8601(value: Any, field: str) -> str:
    text = require_text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return text


def require_string_list(value: Any, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    cleaned = tuple(require_text(item, field) for item in value)
    if not allow_empty and not cleaned:
        raise ValueError(f"{field} must not be empty")
    return cleaned
