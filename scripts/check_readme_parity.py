#!/usr/bin/env python3
"""Check structural and contract parity between the two public READMEs."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGLISH = REPO_ROOT / "README.md"
TRADITIONAL_CHINESE = REPO_ROOT / "README.zh-TW.md"

REQUIRED_CONTRACT_TOKENS = (
    "python -m pip install --upgrade ai-profile-cli",
    "aiprofile init",
    "aiprofile scan .",
    "aiprofile aggregate",
    "aiprofile render",
    "aggregate_only",
    "full",
    "excluded",
    "unknown",
    "AI-attributed commits",
    "Actor presences",
    "HEAD",
    "SHA-1",
    "GitHub Pages",
    "dist/dashboard.html",
    "THIRD_PARTY_NOTICES.md",
)

HEADING_PAIRS = (
    ("Show the evidence behind your AI collaboration.", "讓你的 AI 協作有證據可查。"),
    ("A real GitHub Profile example", "真實 GitHub Profile 範例"),
    ("Why ai-profile?", "為什麼使用 ai-profile？"),
    ("Install", "安裝"),
    ("Quickstart", "快速開始"),
    (
        "Configure identities and repository privacy",
        "設定 identities 與 repository 隱私",
    ),
    ("Scan and refresh multiple repositories", "Scan 與更新多個 repositories"),
    ("Publish to your GitHub Profile", "發布到 GitHub Profile"),
    ("What gets generated", "會產生哪些內容"),
    ("Declare AI participation", "宣告 AI 參與"),
    ("Privacy", "隱私"),
    ("Metrics and current limitations", "指標與目前限制"),
    ("Help, contributing, and license", "說明、貢獻與授權"),
)

CODE_BLOCK_CONTRACTS = (
    ("python -m pip install --upgrade ai-profile-cli", "aiprofile --version"),
    ("python -m aiprofile --version",),
    ("aiprofile init", "aiprofile scan .", "aiprofile aggregate", "aiprofile render"),
    ("dashboard.html", "profile.json", "summary-light.svg", "badge-dark.svg"),
    ('"identities"', '"repositories"', '"salt"'),
    ('"path"', '"repository_uid"', '"publication_level": "aggregate_only"'),
    ("aiprofile aggregate", "aiprofile render"),
    ("aiprofile scan /path/to/repository-one", "aiprofile render"),
    ("<a href=", "dist/dashboard.html", "dist/summary-dark.svg"),
    ("AI-Provider:", "AI-Model:", "AI-Mode:"),
)

REQUIRED_LOCALIZED_CLAIMS = (
    (
        "attribution comes from `AI-*` trailers and\n  verified AI co-author identities",
        "attribution 來自 `AI-*` trailers 與已驗證的 AI\n  co-author identities",
    ),
    (
        "scanning, aggregation, and rendering happen on\n  your machine",
        "scan、aggregate 與 render 都在你的電腦執行",
    ),
    (
        "one render produces theme-aware SVG cards",
        "一次 render 會產生支援主題的 SVG 卡片",
    ),
    (
        "Commits with no explicit evidence\nstay `unknown`",
        "沒有證據的 commit 會維持\n`unknown`",
    ),
    (
        "The CLI makes no network calls, uploads no repository data, and sends no\n  telemetry.",
        "CLI 不會進行網路呼叫、不上傳 repository data，也不傳送 telemetry。",
    ),
    (
        "Public assets contain the UTC generation date",
        "公開資產會包含 UTC generation date",
    ),
    (
        "repository\n  activity dates appear only for `full` repositories",
        "repository activity dates\n  只會來自 `full` repositories",
    ),
)


class ReadmeParityError(RuntimeError):
    """The canonical and localized README contracts have drifted."""


def _heading_levels(text: str) -> list[int]:
    return [len(match.group(1)) for match in re.finditer(r"^(#{1,6})\s+", text, re.MULTILINE)]


def _h2_headings(text: str) -> list[str]:
    return re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE)


def _code_blocks(text: str) -> list[tuple[str, str]]:
    return re.findall(
        r"^```([A-Za-z0-9_-]*)\s*\n(.*?)^```\s*$",
        text,
        re.MULTILINE | re.DOTALL,
    )


def _external_urls(text: str) -> Counter[str]:
    return Counter(
        value.rstrip("`.,;:!?。；：！？")
        for value in re.findall(r"https://[^)\s\"']+", text)
    )


def validate_readme_parity(
    english_path: Path = ENGLISH,
    traditional_chinese_path: Path = TRADITIONAL_CHINESE,
) -> None:
    english = english_path.read_text(encoding="utf-8")
    chinese = traditional_chinese_path.read_text(encoding="utf-8")

    if "## Show the evidence behind your AI collaboration." not in english:
        raise ReadmeParityError("canonical headline is missing")
    if '<img alt=""' not in english or '<img alt=""' not in chinese:
        raise ReadmeParityError("decorative banner must have empty alt text")
    if _heading_levels(english) != _heading_levels(chinese):
        raise ReadmeParityError("heading-level structure differs")
    if list(zip(_h2_headings(english), _h2_headings(chinese), strict=True)) != list(
        HEADING_PAIRS
    ):
        raise ReadmeParityError("ordered public section mapping differs")

    english_blocks = _code_blocks(english)
    chinese_blocks = _code_blocks(chinese)
    if len(english_blocks) != len(CODE_BLOCK_CONTRACTS) or len(chinese_blocks) != len(
        CODE_BLOCK_CONTRACTS
    ):
        raise ReadmeParityError("code-block count differs from the public contract")
    for index, ((english_language, english_body), (chinese_language, chinese_body), tokens) in (
        enumerate(zip(english_blocks, chinese_blocks, CODE_BLOCK_CONTRACTS, strict=True))
    ):
        if english_language != chinese_language:
            raise ReadmeParityError(f"code-block {index} language differs")
        for token in tokens:
            if token not in english_body or token not in chinese_body:
                raise ReadmeParityError(f"code-block {index} is missing {token!r}")

    if _external_urls(english) != _external_urls(chinese):
        raise ReadmeParityError("external link or asset set differs")
    if "(#quickstart)" not in english or "(#快速開始)" not in chinese:
        raise ReadmeParityError("hero quickstart CTA differs")
    live_dashboard = "https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html"
    if english.count(live_dashboard) != chinese.count(live_dashboard):
        raise ReadmeParityError("live-dashboard CTA count differs")

    for token in REQUIRED_CONTRACT_TOKENS:
        missing = [
            label
            for label, text in (("README.md", english), ("README.zh-TW.md", chinese))
            if token not in text
        ]
        if missing:
            raise ReadmeParityError(f"{token!r} missing from {', '.join(missing)}")

    for english_claim, chinese_claim in REQUIRED_LOCALIZED_CLAIMS:
        if english_claim not in english or chinese_claim not in chinese:
            raise ReadmeParityError(f"localized feature/privacy claim differs: {english_claim!r}")

    print("PASS: README English/Traditional Chinese structure and contract parity")


def main() -> int:
    try:
        validate_readme_parity()
    except (OSError, ReadmeParityError) as exc:
        print(f"FAIL: README parity: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
