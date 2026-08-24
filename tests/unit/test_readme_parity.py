"""Public README parity regression."""

from __future__ import annotations

import hashlib
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


def test_profile_cards_use_compact_mobile_sources_in_both_readmes():
    for path in (parity.ENGLISH, parity.TRADITIONAL_CHINESE):
        text = path.read_text(encoding="utf-8")

        assert (
            text.count(
                'media="(max-width: 600px) and (prefers-color-scheme: dark)"'
            )
            == 2
        )
        assert text.count('media="(max-width: 600px)"') == 2
        assert text.count("dist/badge-dark.svg") >= 2
        assert text.count("dist/badge-light.svg") >= 2


def test_candidate_v048_link_evidence_matches_current_readmes():
    """The v0.4.8 candidate README set is covered by the PRE-RELEASE
    candidate evidence file (scope/version asserted), with the exact
    URL-set/status/Markdown-count contract the retained evidence uses.
    The retained POST-RELEASE public evidence
    (promotion-public-link-evidence.json) is pinned here by digest to the
    bytes recorded by the completed v0.4.8 post-release live verification —
    any future change requires a new live verification and a pin update."""
    evidence = json.loads(
        (
            ROOT / "docs" / "reviews" / "promotion-public-link-candidate-v048.json"
        ).read_text(encoding="utf-8")
    )
    urls = {
        url
        for path in (parity.ENGLISH, parity.TRADITIONAL_CHINESE)
        for url in parity._external_urls(path.read_text(encoding="utf-8"))
        if "USERNAME" not in url
    }

    assert evidence["candidate_version"] == "0.4.8"
    assert "Pre-release candidate link evidence" in evidence["scope"]
    assert "v0.4.7" in evidence["scope"]  # honest current-release pointer
    assert set(evidence["urls"]) == urls
    assert set(evidence["urls"].values()) == {200}
    assert evidence["github_markdown"] == {
        "README.md": {"status": 200, "h2": 13, "code_blocks": 10},
        "README.zh-TW.md": {"status": 200, "h2": 13, "code_blocks": 10},
    }
    assert set(evidence["release_urls"]) == {
        "https://pypi.org/project/ai-profile-cli/0.4.7/",
        "https://github.com/WenyuChiou/ai-profile/releases/tag/v0.4.7",
    }
    assert set(evidence["release_urls"].values()) == {200}

    retained = (
        ROOT / "docs" / "reviews" / "promotion-public-link-evidence.json"
    ).read_bytes()
    assert (
        hashlib.sha256(retained).hexdigest()
        == "0e7a10e741476ff298a6e55b915c11a559c31e02efbd7601105033e0d92637a0"
    ), (
        "retained post-release evidence diverged from the v0.4.8 live-verified"
        " bytes; a new live verification must update it (and this pin)"
    )


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
            "Scan、aggregate、refresh 與 render 不會進行網路呼叫，也不傳送 telemetry。",
            "Scan、aggregate、refresh 與 render 可能進行網路呼叫。",
            "claim",
        ),
        (
            "18fb08eb6bca4fac6cb4cd1058cc7641452e7bf3",
            "v0.8.1",
            "missing",
        ),
        ("AIPROFILE_IDENTITIES", "IDENTITIES", "missing"),
        ("暫時性的 `-shm`", "永久性的 `-shm`", "claim"),
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
