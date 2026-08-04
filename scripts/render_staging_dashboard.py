#!/usr/bin/env python3
"""Deterministic synthetic staging preview for a pinned candidate wheel.

Renders the UNMODIFIED ``render_dashboard`` output of whichever ``aiprofile``
package is importable by the interpreter running this script. The staging
workflow (.github/workflows/staging-preview.yml) runs it with a fresh venv
python that has ONLY the exact built candidate wheel installed, so the
rendered bytes are the candidate renderer's own output — nothing here wraps
the page or injects CSS/JS into it.

The input is a fixed, synthetic, public-only ``VizStats`` fixture. VizStats
is the structural privacy boundary (src/aiprofile/viz.py): a validated
instance can only carry canonical provider vocabulary, closed period/date
strings, and counts — repository names, paths, organizations, emails, SHAs,
URLs, and prompts are unrepresentable. The fixture numbers below are
invented and identified as such by ``FIXTURE_ID`` in the manifest.

Outputs exactly two files in ``--out`` (which must be empty or contain only
a previous run's outputs):

- ``dashboard.html`` — the exact candidate render of the fixture;
- ``staging-manifest.json`` — format version, installed package version,
  computed candidate-wheel SHA-256, computed dashboard SHA-256, and the
  fixture identifier. No timestamp, hostname, path, or other run-local data.

Every byte is a pure function of the wheel bytes, the installed renderer,
and this file: no clock, randomness, locale, or network dependence.

Usage:

    python scripts/render_staging_dashboard.py \\
        --wheel dist/ai_profile_cli-X.Y.Z-py3-none-any.whl \\
        --out staging/vX.Y.Z
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from aiprofile import ACE_SCHEMA_VERSION, __version__
from aiprofile.render.dashboard_html import render_dashboard
from aiprofile.viz import (
    DayCell,
    DayCount,
    EvidenceTotals,
    ModelRow,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
)

#: Bumped only when the manifest key set or semantics change.
MANIFEST_FORMAT = "aiprofile-staging-manifest/1"

#: Names the fixed fixture below; a changed fixture needs a new identifier.
FIXTURE_ID = "synthetic-two-provider-fixture-v2-model-ledger"

_OUTPUT_NAMES = frozenset({"dashboard.html", "staging-manifest.json"})


def build_fixture() -> VizStats:
    """The fixed synthetic preview fixture: two providers plus a mixed and a
    zero-attributed-AI day, so provider filter, calendar, and evidence
    behavior are all browser-verifiable. All values are invented; validation
    pins every string to the closed public vocabulary."""
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(None, None, "All time"),
        totals=Totals(
            commits_scanned=40,
            ai_attributed_commits=24,
            ai_actor_presences=26,
            human_declared_commits=6,
            unknown_commits=10,
            active_ai_days=11,
        ),
        providers=(
            ProviderRow("anthropic", "Claude", 16, 17, 9),
            ProviderRow("openai", "OpenAI", 10, 9, 6),
        ),
        provider_count=2,
        models=(
            ModelRow("claude", "Claude", 15, 15, 8),
            ModelRow("gpt", "GPT", 9, 9, 5),
            ModelRow("unknown", "Unknown", 2, 2, 2),
        ),
        model_count=2,
        evidence=EvidenceTotals(
            verified=4,
            declared=20,
            imported=2,
            inferred=0,
            unknown=16,
            total_records=42,
        ),
        privacy=PrivacySplit(28, 12, True),
        generated_on="2026-01-01",
        daily=(
            DayCell(
                "2025-12-01",
                (DayCount("anthropic", 2),),
                total_commits=3,
                ai_commits=2,
            ),
            DayCell(
                "2025-12-02",
                (DayCount("anthropic", 1), DayCount("openai", 1)),
                total_commits=4,
                ai_commits=2,
            ),
            DayCell(
                "2025-12-05",
                (DayCount("openai", 2),),
                total_commits=2,
                ai_commits=2,
            ),
            DayCell("2025-12-09", (), total_commits=2, ai_commits=0),
            DayCell(
                "2025-12-15",
                (DayCount("anthropic", 3), DayCount("openai", 1)),
                total_commits=5,
                ai_commits=4,
            ),
            DayCell(
                "2026-01-01",
                (DayCount("anthropic", 2),),
                total_commits=2,
                ai_commits=2,
            ),
        ),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_staging(wheel: Path, out_dir: Path) -> dict:
    wheel = wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise SystemExit(f"candidate wheel not found: {wheel}")
    out_dir.mkdir(parents=True, exist_ok=True)
    foreign = sorted(p.name for p in out_dir.iterdir() if p.name not in _OUTPUT_NAMES)
    if foreign:
        raise SystemExit(
            f"output directory {out_dir} contains unexpected entries {foreign};"
            " the staging directory must hold exactly the two staging outputs"
        )

    dashboard_path = out_dir / "dashboard.html"
    dashboard_path.write_bytes(render_dashboard(build_fixture()).encode("utf-8"))

    manifest = {
        "format_version": MANIFEST_FORMAT,
        "package_version": __version__,
        "wheel_sha256": _sha256(wheel),
        "dashboard_sha256": _sha256(dashboard_path),
        "fixture_id": FIXTURE_ID,
    }
    (out_dir / "staging-manifest.json").write_bytes(
        (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("ascii")
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = render_staging(args.wheel, args.out)
    print(json.dumps(manifest, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
