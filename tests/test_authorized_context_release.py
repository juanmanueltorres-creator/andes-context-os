import json
from pathlib import Path
import tomllib

from andes_context_os.producers.authorized_context import AuthorizedContextManifest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "authorized_context.example.v0.1.json"
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"
PRODUCER = ROOT / "src" / "andes_context_os" / "producers" / "authorized_context.py"


def test_public_example_is_fictitious_and_safe():
    manifest = AuthorizedContextManifest.load(SAMPLE)
    assert len(manifest.entries) == 2
    for entry in manifest.entries:
        assert entry.context.sensitivity.value == "public"
        assert entry.resolver_id == "example"
        assert entry.source_locator.startswith("example://")
        assert "github.com" not in entry.source_locator
        assert "juanmanueltorres" not in repr(entry.to_dict()).lower()


def test_public_example_has_no_secret_like_keys():
    text = repr(json.loads(SAMPLE.read_text(encoding="utf-8"))).lower()
    for forbidden in (
        "password",
        "api_key",
        "access_token",
        "authorization",
        "cookie",
        "private_aoi",
    ):
        assert forbidden not in text


def test_v03_adds_no_runtime_dependency_or_network_client():
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == []
    source = PRODUCER.read_text(encoding="utf-8").lower()
    for forbidden in (
        "requests",
        "httpx",
        "github",
        "mcp",
        "openai",
        "anthropic",
        "supabase",
    ):
        assert f"import {forbidden}" not in source
        assert f"from {forbidden}" not in source


def test_readme_describes_v03_without_live_connector_claim():
    text = README.read_text(encoding="utf-8")
    assert "## V0.3 — Authorized Context Producer" in text
    assert "exact authorized references" in text
    assert "does not search GitHub or the private vault" in text
    assert "source content is not copied into the produced catalog" in text
