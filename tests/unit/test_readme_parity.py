"""Public README parity regression."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_readme_parity.py"
SPEC = importlib.util.spec_from_file_location("check_readme_parity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def test_public_readmes_have_structural_and_contract_parity():
    parity.validate_readme_parity()


def test_retained_public_link_evidence_matches_current_readmes():
    evidence = json.loads(
        (ROOT / "docs" / "reviews" / "promotion-public-link-evidence.json").read_text(
            encoding="utf-8"
        )
    )
    urls = {
        url
        for path in (parity.ENGLISH, parity.TRADITIONAL_CHINESE)
        for url in parity._external_urls(path.read_text(encoding="utf-8"))
        if "USERNAME" not in url
    }

    assert set(evidence["urls"]) == urls
    assert set(evidence["urls"].values()) == {200}
    assert evidence["github_markdown"] == {
        "README.md": {"status": 200, "h2": 13, "code_blocks": 10},
        "README.zh-TW.md": {"status": 200, "h2": 13, "code_blocks": 10},
    }


def test_parity_rejects_missing_privacy_contract(tmp_path):
    english = tmp_path / "README.md"
    chinese = tmp_path / "README.zh-TW.md"
    english.write_text(parity.ENGLISH.read_text(encoding="utf-8"), encoding="utf-8")
    source = parity.TRADITIONAL_CHINESE.read_text(encoding="utf-8")
    chinese.write_text(source.replace("aggregate_only", "aggregate-only"), encoding="utf-8")

    with pytest.raises(parity.ReadmeParityError, match="aggregate_only"):
        parity.validate_readme_parity(english, chinese)


@pytest.mark.parametrize(
    ("needle", "replacement", "message"),
    [
        ("(#快速開始)", "(#其他段落)", "CTA"),
        ("一次 render 會產生支援主題的 SVG 卡片", "一次 render 會產生檔案", "claim"),
        (
            "CLI 不會進行網路呼叫、不上傳 repository data，也不傳送 telemetry。",
            "CLI 可能進行網路呼叫。",
            "claim",
        ),
    ],
)
def test_parity_rejects_cta_feature_and_privacy_drift(
    tmp_path,
    needle,
    replacement,
    message,
):
    english = tmp_path / "README.md"
    chinese = tmp_path / "README.zh-TW.md"
    english.write_text(parity.ENGLISH.read_text(encoding="utf-8"), encoding="utf-8")
    source = parity.TRADITIONAL_CHINESE.read_text(encoding="utf-8")
    assert needle in source
    chinese.write_text(source.replace(needle, replacement, 1), encoding="utf-8")

    with pytest.raises(parity.ReadmeParityError, match=message):
        parity.validate_readme_parity(english, chinese)
