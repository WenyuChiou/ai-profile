"""VizStats — the visualization data contract and privacy redaction boundary
(architecture.md sections 3 and 8).

Renderers and exporters accept only this type, and validation ENFORCES the
boundary (gate-7 H-01): every string field is pinned to a closed public
vocabulary — the ACE schema version, the fixed v0.1 all-time period,
canonical provider slugs, and the schema-owned display name for each slug.
Repository identity, emails, shas, paths, org names, and raw trailer
strings are therefore structurally unrepresentable in a VALIDATED instance,
not merely absent from the supported constructor path
(privacy.build_viz_stats remains the only production builder).
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass

from . import ACE_SCHEMA_VERSION
from .errors import RenderError
from .schema.vocab import (
    CANONICAL_PROVIDERS,
    PROVIDER_DISPLAY,
    UNRECOGNIZED_DISPLAY,
    UNRECOGNIZED_PROVIDER,
)

#: The single period the v0.1 contract can express (schema.md section 15:
#: the v0.1 reporting period is all-time with null bounds). Post-v0.1
#: period support must extend this contract, not free-text it.
V01_PERIOD_LABEL = "All time"

#: ASCII-only, fullmatched (gate-8 L-01): Python's \d accepts Unicode
#: decimals and `$` tolerates a trailing newline — both reproduced
#: bypasses. Calendar validity is checked separately via
#: date.fromisoformat + round-trip.
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

#: Maximum span of the daily activity series (round D2, ADR-018; widened
#: 84 → 365 by round D4's heatmap, ADR-018 addendum): the series
#: publishes at most a year of publishable-repo activity. A hard
#: contract bound, not a renderer preference — a validated instance
#: cannot carry an unbounded activity history. (The isometric band
#: renders only its own last-84-day slice of this series.)
DAILY_WINDOW_DAYS = 365


@dataclass(frozen=True)
class Period:
    from_date: str | None
    to_date: str | None
    label: str


@dataclass(frozen=True)
class Totals:
    commits_scanned: int
    ai_attributed_commits: int
    ai_actor_presences: int   # one provider/tool tuple per commit (G2-02)
    human_declared_commits: int
    unknown_commits: int
    active_ai_days: int       # commit author dates (G2-18)


@dataclass(frozen=True)
class ProviderRow:
    provider: str
    display_name: str
    attributed_commits: int   # unit: commits (schema.md section 15)
    actor_presences: int       # unit: presences (G2-02)
    active_days: int           # unit: days (author dates)


@dataclass(frozen=True)
class EvidenceTotals:
    # unit: records; population = ALL ACE records, every actor type
    # (schema.md section 15, G2-05). Categories must sum to total_records.
    verified: int
    declared: int
    imported: int
    inferred: int
    unknown: int
    total_records: int


@dataclass(frozen=True)
class PrivacySplit:
    # Policy-based labels, never visibility claims (G2-04): "publishable"
    # records the user's `full` decision, not verified GitHub visibility.
    explicitly_publishable_commits: int
    anonymous_aggregate_commits: int
    includes_anonymous_aggregate: bool


@dataclass(frozen=True)
class DayCount:
    # One provider's attributed-commit count on one calendar day
    # (round D2, ADR-018). Same commit-unit semantic as ProviderRow.
    provider: str             # canonical slug or the unrecognized bucket
    attributed_commits: int   # unit: commits; strictly positive


@dataclass(frozen=True)
class DayCell:
    # One calendar day of the publishable-only activity series
    # (ADR-018): dates from repositories the owner explicitly marked
    # publishable — aggregate-only repositories NEVER contribute here.
    # Round D4 (.ai/round_d4_heatmap_spec.md) adds the day's WHOLE
    # rhythm: total_commits counts every commit the owner authored that
    # day (human-only included — the heatmap's intensity axis), and
    # ai_commits counts the distinct AI/mixed subset (the hue axis).
    date: str                        # YYYY-MM-DD, generated_on-class rules
    counts: tuple[DayCount, ...]     # slug-ascending, unique; empty IFF
    #                                  ai_commits == 0 (human-only day)
    total_commits: int               # all actors; strictly positive
    ai_commits: int                  # distinct ai/mixed commits;
    #                                  0 <= ai_commits <= total_commits


@dataclass(frozen=True)
class VizStats:
    schema_version: str
    period: Period
    totals: Totals
    providers: tuple[ProviderRow, ...]
    provider_count: int   # distinct providers excluding the unrecognized bucket
    evidence: EvidenceTotals
    privacy: PrivacySplit
    generated_on: str     # UTC date, YYYY-MM-DD — never a full timestamp
    # Publishable-only daily series (round D2, ADR-018). Empty = no
    # calendar band. Defaults to empty so the field is additive for
    # existing constructor sites; validation runs regardless.
    daily: tuple[DayCell, ...] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        # SEAL against subclassing at class-definition time (gate-9 H-01):
        # VizStats IS the privacy boundary, and a subclass is an ordinary
        # Python construct that defeats every in-method guard — it can
        # override __getattribute__ to substitute a private-canary row at
        # render time, or simply override __post_init__ to skip validation
        # entirely. Checking type() inside _validate is whack-a-mole
        # (a subclass can decline to call it); raising here closes the
        # whole family — no subclass can even be defined. Nothing legit
        # subclasses VizStats (replace/copy/pickle all yield exact
        # VizStats), so this breaks nothing.
        raise TypeError(
            "VizStats must not be subclassed - it is the privacy boundary;"
            " any subclass can override __post_init__/__getattribute__ to"
            " bypass validation and publish arbitrary private text"
        )

    def __post_init__(self) -> None:
        _validate(self)


def _require_exact(value: object, expected: type, what: str) -> None:
    # Exact-type check, deliberately NOT isinstance (gate-8 H-01): a
    # subclass — or any duck type — can be mutable or emit different
    # text at render time than validation saw. Rejection over coercion,
    # matching the schema layer's own philosophy.
    if type(value) is not expected:
        raise RenderError(
            f"VizStats: {what} must be exact {expected.__name__},"
            f" got {type(value).__name__}"
        )


def _require_canonical_date(value: str, what: str) -> None:
    # Shared date battery (gate-8 L-01, reused for the D2 daily series):
    # ASCII fullmatch kills Unicode decimals and trailing newlines;
    # fromisoformat + round-trip kills impossible and non-canonical forms.
    if not _DATE_RE.fullmatch(value):
        raise RenderError(
            f"VizStats {what} must be an ASCII YYYY-MM-DD date, never a"
            " timestamp"
        )
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise RenderError(
            f"VizStats {what} is not a real calendar date: {exc}"
        ) from exc
    if parsed.isoformat() != value:
        raise RenderError(
            f"VizStats {what} must be the canonical YYYY-MM-DD form"
        )


def _validate(s: VizStats) -> None:
    # ---- Exact TOP-LEVEL type backstop (gate-9 H-01): subclassing is
    # already sealed at class-definition time by __init_subclass__, so no
    # ordinary subclass can reach here. This is cheap defense-in-depth
    # for any exotic instance (e.g. a custom metaclass that skips
    # __init_subclass__) that still routes through __post_init__.
    if type(s) is not VizStats:
        raise RenderError(
            f"VizStats must be exact VizStats, not {type(s).__name__}"
        )
    # ---- Structural immutability of the validated graph (gate-8 H-01),
    # enforced BEFORE any duck-typed attribute access below: a mutable
    # provider list, a tuple holding a mutable row-like object, and a
    # mutable period-like object all passed validation and published
    # post-construction mutations through BOTH render_summary and
    # dumps_stats (reproduced). Exact frozen contract types close every
    # probe: after this block the whole graph is frozen dataclasses,
    # tuples, plain str/int/bool/None leaves.
    _require_exact(s.period, Period, "period")
    _require_exact(s.totals, Totals, "totals")
    _require_exact(s.evidence, EvidenceTotals, "evidence")
    _require_exact(s.privacy, PrivacySplit, "privacy")
    _require_exact(s.providers, tuple, "providers container")
    for row in s.providers:
        _require_exact(row, ProviderRow, "each provider row")
    # String leaves must be exact str (gate-8 H-01): a str subclass can
    # override __str__/__format__ and emit text validation never saw.
    for value, what in (
        (s.schema_version, "schema_version"),
        (s.period.label, "period.label"),
        (s.generated_on, "generated_on"),
        *((r.provider, "provider slug") for r in s.providers),
        *((r.display_name, "display name") for r in s.providers),
    ):
        if type(value) is not str:
            raise RenderError(f"VizStats: {what} must be exact str")

    counts = [
        s.totals.commits_scanned,
        s.totals.ai_attributed_commits,
        s.totals.ai_actor_presences,
        s.totals.human_declared_commits,
        s.totals.unknown_commits,
        s.totals.active_ai_days,
        s.evidence.verified,
        s.evidence.declared,
        s.evidence.imported,
        s.evidence.inferred,
        s.evidence.unknown,
        s.evidence.total_records,
        s.privacy.explicitly_publishable_commits,
        s.privacy.anonymous_aggregate_commits,
        s.provider_count,
        # provider-row numerics (gate M-01): rows are part of the validated
        # contract too, not just the top-level totals.
        *(p.attributed_commits for p in s.providers),
        *(p.actor_presences for p in s.providers),
        *(p.active_days for p in s.providers),
    ]
    # Exact int, deliberately not isinstance (gate-8 code-review pass):
    # an int SUBCLASS can override __str__ and emit render-time text
    # validation never saw (reproduced: EvilInt leaked into the SVG),
    # and bool is an int subclass. Same rejection rule as the str leaves.
    if any(type(c) is not int or c < 0 for c in counts):
        raise RenderError(
            "VizStats: all counts must be exact int and non-negative"
        )
    if type(s.privacy.includes_anonymous_aggregate) is not bool:
        raise RenderError(
            "VizStats: includes_anonymous_aggregate must be exact bool"
        )
    # Canonical ASCII calendar date (gate-8 L-01), shared battery.
    _require_canonical_date(s.generated_on, "generated_on")
    if (
        s.privacy.explicitly_publishable_commits
        + s.privacy.anonymous_aggregate_commits
        != s.totals.commits_scanned
    ):
        raise RenderError(
            "VizStats: publishable + anonymous-aggregate commits must equal"
            " commits_scanned"
        )
    if s.privacy.includes_anonymous_aggregate != (
        s.privacy.anonymous_aggregate_commits > 0
    ):
        raise RenderError(
            "VizStats: includes_anonymous_aggregate flag inconsistent with counts"
        )
    evidence_sum = (
        s.evidence.verified
        + s.evidence.declared
        + s.evidence.imported
        + s.evidence.inferred
        + s.evidence.unknown
    )
    if evidence_sum != s.evidence.total_records:
        raise RenderError(
            "VizStats: evidence categories must sum to total_records (G2-05)"
        )
    if sum(p.actor_presences for p in s.providers) != s.totals.ai_actor_presences:
        raise RenderError(
            "VizStats: provider actor_presences rows must sum to"
            " totals.ai_actor_presences"
        )
    if s.totals.ai_attributed_commits > s.totals.commits_scanned:
        raise RenderError(
            "VizStats: ai_attributed_commits cannot exceed commits_scanned"
        )
    if any(
        p.attributed_commits > s.totals.ai_attributed_commits for p in s.providers
    ):
        raise RenderError(
            "VizStats: a provider attributed_commits value cannot exceed the"
            " AI-attributed total"
        )
    expected_rank = sorted(
        s.providers, key=lambda p: (-p.attributed_commits, p.provider)
    )
    if list(s.providers) != expected_rank:
        raise RenderError(
            "VizStats.providers must be ranked by attributed_commits desc, slug asc"
        )
    real = [p for p in s.providers if p.provider != UNRECOGNIZED_PROVIDER]
    if s.provider_count != len(real):
        raise RenderError(
            "VizStats.provider_count must equal providers excluding the"
            " unrecognized bucket"
        )
    # ---- Structural privacy boundary for STRING fields (gate-7 H-01):
    # a validated VizStats must be unable to carry arbitrary text into
    # SVG/JSON. Every string is pinned to a closed public vocabulary; the
    # reproduced leak (canary period label / display name published
    # verbatim) fails HERE, before any renderer runs.
    if s.schema_version != ACE_SCHEMA_VERSION:
        raise RenderError(
            f"VizStats.schema_version must be the supported ACE version"
            f" ({ACE_SCHEMA_VERSION!r}); free-form version strings are not"
            " publishable"
        )
    if (
        s.period.from_date is not None
        or s.period.to_date is not None
        or s.period.label != V01_PERIOD_LABEL
    ):
        raise RenderError(
            "VizStats.period: the v0.1 contract is the all-time period"
            f" (bounds None, label {V01_PERIOD_LABEL!r}); free-form period"
            " text is not publishable"
        )
    # ---- Publishable-only daily series (round D2, ADR-018). Same
    # battery as every other nested record: exact container/record
    # types BEFORE duck-typed access, exact str/int leaves, closed
    # vocabulary, and cross-checks that pin the series as an honest
    # SUBSET of the provider rows.
    _require_exact(s.daily, tuple, "daily container")
    for cell in s.daily:
        _require_exact(cell, DayCell, "each day cell")
        _require_exact(cell.counts, tuple, "day cell counts container")
        for dc in cell.counts:
            _require_exact(dc, DayCount, "each day count")
            if type(dc.provider) is not str:
                raise RenderError("VizStats: day count provider must be exact str")
            if type(dc.attributed_commits) is not int or dc.attributed_commits < 1:
                raise RenderError(
                    "VizStats: day count attributed_commits must be exact int"
                    " and strictly positive - zero-activity entries are omitted,"
                    " not stored"
                )
        if type(cell.date) is not str:
            raise RenderError("VizStats: day cell date must be exact str")
        _require_canonical_date(cell.date, "daily date")
        # ---- Round D4 whole-rhythm fields (.ai/round_d4_heatmap_spec.md):
        # exact ints, total strictly positive (a cell exists only for
        # days with commits), 0 <= ai_commits <= total_commits.
        if type(cell.total_commits) is not int or cell.total_commits < 1:
            raise RenderError(
                "VizStats: day cell total_commits must be exact int and"
                " strictly positive - zero-commit days are omitted, not stored"
            )
        if type(cell.ai_commits) is not int or cell.ai_commits < 0:
            raise RenderError(
                "VizStats: day cell ai_commits must be exact int and non-negative"
            )
        if cell.ai_commits > cell.total_commits:
            raise RenderError(
                "VizStats: day cell ai_commits cannot exceed total_commits -"
                " the AI subset cannot be larger than the day's whole"
            )
        # counts is the per-provider breakdown of ai_commits: empty IFF
        # the day had zero AI commits (human-only day). When present,
        # each provider's distinct-commit count is a subset of the day's
        # distinct AI commits (count <= ai_commits), and every AI commit
        # surfaces in >=1 count (ai_commits <= sum).
        if cell.ai_commits == 0 and cell.counts:
            raise RenderError(
                "VizStats: day cell counts must be empty when ai_commits is 0"
            )
        if cell.ai_commits > 0 and not cell.counts:
            raise RenderError(
                "VizStats: day cell counts must be non-empty when ai_commits > 0"
                " - an AI count with no provider breakdown cannot be cross-checked"
            )
        if cell.counts:
            if max(dc.attributed_commits for dc in cell.counts) > cell.ai_commits:
                raise RenderError(
                    "VizStats: a day cell provider count exceeds ai_commits -"
                    " each provider's commits are a subset of the day's AI commits"
                )
            if cell.ai_commits > sum(dc.attributed_commits for dc in cell.counts):
                raise RenderError(
                    "VizStats: day cell ai_commits exceeds the sum of its provider"
                    " counts - every AI commit carries at least one provider presence"
                )
        slugs = [dc.provider for dc in cell.counts]
        if slugs != sorted(slugs) or len(set(slugs)) != len(slugs):
            raise RenderError(
                "VizStats: day cell counts must be slug-ascending and unique"
            )
    dates = [cell.date for cell in s.daily]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise RenderError(
            "VizStats.daily must be date-ascending without duplicates"
        )
    if s.daily:
        span = (
            datetime.date.fromisoformat(dates[-1])
            - datetime.date.fromisoformat(dates[0])
        ).days
        if span >= DAILY_WINDOW_DAYS or len(s.daily) > DAILY_WINDOW_DAYS:
            raise RenderError(
                f"VizStats.daily must span fewer than {DAILY_WINDOW_DAYS} days"
                " (ADR-018 window bound, widened by the D4 addendum)"
            )
        row_totals = {p.provider: p.attributed_commits for p in s.providers}
        daily_totals: dict[str, int] = {}
        for cell in s.daily:
            for dc in cell.counts:
                daily_totals[dc.provider] = (
                    daily_totals.get(dc.provider, 0) + dc.attributed_commits
                )
        for slug, total in daily_totals.items():
            if slug not in row_totals:
                raise RenderError(
                    f"VizStats.daily carries provider {slug!r} with no matching"
                    " provider row - the series must be a subset of the rows"
                )
            if total > row_totals[slug]:
                raise RenderError(
                    f"VizStats.daily total for {slug!r} exceeds that provider's"
                    " attributed_commits - the publishable subset cannot be"
                    " larger than the whole"
                )

    allowed_slugs = CANONICAL_PROVIDERS | {UNRECOGNIZED_PROVIDER}
    for cell in s.daily:
        for dc in cell.counts:
            if dc.provider not in allowed_slugs:
                raise RenderError(
                    f"VizStats daily provider slug {dc.provider!r} is not in"
                    " the canonical public vocabulary"
                )
    for row in s.providers:
        if row.provider not in allowed_slugs:
            raise RenderError(
                f"VizStats provider slug {row.provider!r} is not in the"
                " canonical public vocabulary (schema.md section 10)"
            )
        expected_display = (
            UNRECOGNIZED_DISPLAY
            if row.provider == UNRECOGNIZED_PROVIDER
            else PROVIDER_DISPLAY.get(row.provider, row.provider)
        )
        if row.display_name != expected_display:
            raise RenderError(
                f"VizStats display name for {row.provider!r} must be the"
                f" schema-owned public display {expected_display!r} -"
                " arbitrary display text is not publishable"
            )


def to_json_dict(s: VizStats) -> dict:
    return {
        "schema_version": s.schema_version,
        "generated_on": s.generated_on,
        "period": {
            "from": s.period.from_date,
            "to": s.period.to_date,
            "label": s.period.label,
        },
        "totals": {
            "commits_scanned": s.totals.commits_scanned,
            "ai_attributed_commits": s.totals.ai_attributed_commits,
            "ai_actor_presences": s.totals.ai_actor_presences,
            "human_declared_commits": s.totals.human_declared_commits,
            "unknown_commits": s.totals.unknown_commits,
            "active_ai_days": s.totals.active_ai_days,
        },
        "providers": [
            {
                "provider": p.provider,
                "display_name": p.display_name,
                "attributed_commits": p.attributed_commits,
                "actor_presences": p.actor_presences,
                "active_days": p.active_days,
            }
            for p in s.providers
        ],
        "provider_count": s.provider_count,
        "evidence_records": {
            "verified": s.evidence.verified,
            "declared": s.evidence.declared,
            "imported": s.evidence.imported,
            "inferred": s.evidence.inferred,
            "unknown": s.evidence.unknown,
            "total_records": s.evidence.total_records,
        },
        "privacy": {
            "explicitly_publishable_commits": s.privacy.explicitly_publishable_commits,
            "anonymous_aggregate_commits": s.privacy.anonymous_aggregate_commits,
            "includes_anonymous_aggregate": s.privacy.includes_anonymous_aggregate,
        },
        # Publishable-only daily series (ADR-018): additive field; empty
        # list when no explicitly-publishable activity exists.
        "daily": [
            {
                "date": cell.date,
                "counts": [
                    {
                        "provider": dc.provider,
                        "attributed_commits": dc.attributed_commits,
                    }
                    for dc in cell.counts
                ],
                # Round D4 whole-rhythm fields (additive; heatmap axes).
                "total_commits": cell.total_commits,
                "ai_commits": cell.ai_commits,
            }
            for cell in s.daily
        ],
    }


def dumps_stats(s: VizStats) -> str:
    """Deterministic profile.json body (mvp.md section 7 test 17)."""
    return json.dumps(to_json_dict(s), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
