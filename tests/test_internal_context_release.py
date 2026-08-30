from pathlib import Path

from andes_context_os.internal_context import ContextSensitivity, InternalContextCatalog

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = ROOT / "data" / "internal_context.example.v0.1.json"
README_PATH = ROOT / "README.md"


def test_example_catalog_loads_and_is_public_safe():
    catalog = InternalContextCatalog.load(EXAMPLE_PATH)
    assert len(catalog.records) == 3
    assert all(record.sensitivity is ContextSensitivity.PUBLIC for record in catalog.records)
    serialized = repr(catalog.to_dict()).lower()
    for forbidden in ("password", "api_key", "access_token", "cookie", "private aoi"):
        assert forbidden not in serialized


def test_readme_describes_v02_without_live_connector_claims():
    text = README_PATH.read_text(encoding="utf-8")
    assert "V0.2 — Internal Context Adapter" in text
    assert "local deterministic catalog" in text
    assert "does not read GitHub or the private vault" in text
    assert "internal context match != evidence validation" in text
