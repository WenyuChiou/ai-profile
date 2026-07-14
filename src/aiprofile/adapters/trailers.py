"""Git trailer adapter: trailer lines → ParticipationSpec (ADR-005).

INTERFACE PINNED BY THE ORCHESTRATOR — work package B implements
parse_commit_trailers without changing any signature or dataclass here.
Normative behavior: ADR-005 (grouping rule + carved exceptions),
schema.md sections 5 and 10, ADR-013 (registry matching).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ..registry import match_coauthor, normalize_provider, resolve_tool
from ..schema.event import ProvenanceSource
from ..schema.vocab import ActorType, ContributionMode, EvidenceLevel, Role, SourceType

#: Recognized AI-* trailer keys (case-insensitive; ADR-005).
AI_TRAILER_KEYS = frozenset(
    {"ai-provider", "ai-model", "ai-tool", "ai-role", "ai-mode", "ai-reviewed-by", "ai-schema"}
)
COAUTHOR_KEY = "co-authored-by"


@dataclass(frozen=True)
class ParticipationSpec:
    """One AI actor presence (or human declaration) parsed from explicit
    trailer evidence. The scanner turns specs into validated ACE events;
    the adapter never invents data."""

    actor_type: ActorType
    provider: str | None
    provider_raw: str | None
    model: str | None       # lowercase(trim(model_raw)) — no registry (schema.md 10)
    model_raw: str | None
    tool: str | None
    tool_raw: str | None
    roles: tuple[Role, ...]
    contribution_mode: ContributionMode | None
    human_reviewed: bool | None
    source: ProvenanceSource


@dataclass(frozen=True)
class ParseWarning:
    """Diagnostics-hygiene-safe warning (architecture.md section 10): `code`
    and `trailer_key` are always safe to print; `local_detail` may quote
    trailer values and is shown only under --verbose."""

    code: str          # unknown-role | malformed-mode | malformed-reviewed-by |
                       # incomplete-group | contradictory-group
    trailer_key: str
    local_detail: str | None = None


def parse_commit_trailers(
    trailer_lines: Sequence[str],
) -> tuple[list[ParticipationSpec], list[ParseWarning]]:
    """Parse one commit's trailer block (ordered lines from
    %(trailers:only,unfold)) into actor-presence specs.

    Contract (implemented by work package B):
    - Trailer lines split on the first ':'; keys matched case-insensitively;
      non-trailer-shaped lines ignored.
    - AI-* grouping: iterate AI-* trailers in order; a repeated key inside
      the current group closes it and starts a new one (ADR-005).
    - A group yields an AI spec when AI-Provider is present (registry
      normalization; unrecognized → provider None + provider_raw kept) or
      AI-Tool resolves via registry.resolve_tool (which supplies the
      provider). Groups with neither are dropped: warning `incomplete-group`.
    - `AI-Mode: Human-Only` in a group with NO AI-Provider/AI-Tool key →
      one HUMAN spec (all identity fields None, evidence declared). With
      any AI-Provider or AI-Tool key present (recognized by the registry
      or not) → drop the whole group: warning `contradictory-group`.
    - AI-Role: comma-separated tokens → Role vocabulary; unknown tokens
      dropped with warning `unknown-role`; empty result = no roles.
    - AI-Mode: vocabulary values matched case-insensitively with '-'/'_'
      equivalence ("AI-Assisted" → ai_assisted); unparseable → None +
      warning `malformed-mode`. Missing mode on an AI group → None (the
      group itself declares AI; schema.md section 5).
    - AI-Reviewed-By: "human" → True, "none" → False, else None + warning
      `malformed-reviewed-by`.
    - AI-Schema: informational only, never affects parsing.
    - Co-authored-by: value shaped "Name <email>"; registry.match_coauthor
      (exact email + optional name-prefix condition) → one AI spec with
      source git_trailer_coauthor, model/model_raw None, provider_raw set
      to the display name. Non-matching co-authors are ignored silently
      (they are presumed human co-authors, not evidence of anything).
    - Sources: git_trailer / git_trailer_coauthor, evidence declared,
      source_reference = the matched trailer key (never a value).
    - Never raises on message content; returns ([], []) for no evidence.
    - Same provider+tool in several groups is fine — the scanner merges by
      identity; the parser does not deduplicate.
    """
    specs: list[ParticipationSpec] = []
    warnings: list[ParseWarning] = []

    # `pending` holds, in message order, either an in-progress AI-* group
    # or an already-resolved co-author ParticipationSpec. Co-author lines
    # never depend on later lines so they are resolved immediately; AI-*
    # groups are finalized only after the loop so a group left open at
    # end-of-input is handled identically to one closed early by a repeated
    # key (ADR-005). A group tracks VALUES and KEY PRESENCE separately
    # (gate M-03): an empty-valued `AI-Provider:` contributes no value but
    # its presence still matters to the Human-Only contradiction rule.
    pending: list[_Group | ParticipationSpec] = []
    current_group: _Group | None = None

    for line in trailer_lines:
        key, value = _split_trailer_line(line)
        if key is None:
            continue

        if key == COAUTHOR_KEY:
            if value:
                coauthor_spec = _parse_coauthor(value)
                if coauthor_spec is not None:
                    pending.append(coauthor_spec)
            continue

        if key not in AI_TRAILER_KEYS:
            # Non-AI, non-co-author trailers are ignored without affecting
            # grouping.
            continue

        if current_group is None:
            current_group = _Group()
            pending.append(current_group)
        elif value and key in current_group.values:
            # Only a NON-EMPTY repeat closes the group (ADR-005): an
            # empty-valued repeat contributes presence without splitting.
            current_group = _Group()
            pending.append(current_group)
        current_group.present.add(key)
        if value:
            current_group.values[key] = value

    for item in pending:
        if isinstance(item, _Group):
            spec, group_warnings = _finalize_group(item)
            warnings.extend(group_warnings)
            if spec is not None:
                specs.append(spec)
        else:
            specs.append(item)

    return specs, warnings


class _Group:
    """One AI-* trailer group: parsed non-empty values plus the set of
    recognized keys that APPEARED (even with empty values — gate M-03)."""

    __slots__ = ("values", "present")

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.present: set[str] = set()


def _split_trailer_line(line: str) -> tuple[str | None, str]:
    """Split one already-unfolded trailer line on the first ':'. A line with
    no ':' yields (None, "") so the caller ignores it; the key is lowercased
    and both sides are stripped (docstring contract)."""
    key_part, sep, value_part = line.partition(":")
    if not sep:
        return None, ""
    return key_part.strip().lower(), value_part.strip()


def _finalize_group(group: _Group) -> tuple[ParticipationSpec | None, list[ParseWarning]]:
    """Turn one collected AI-* trailer group into a spec, or drop it with a
    group-level warning (ADR-005 grouping rule + the two carved Human-Only
    exceptions; schema.md section 5)."""
    values = group.values
    provider_raw_value = values.get("ai-provider")
    tool_raw_value = values.get("ai-tool")
    tool_resolved = resolve_tool(tool_raw_value) if tool_raw_value is not None else None
    has_anchor = provider_raw_value is not None or tool_resolved is not None

    mode_raw_value = values.get("ai-mode")
    mode_candidate = _normalize_mode(mode_raw_value) if mode_raw_value is not None else None
    is_human_only = mode_candidate is ContributionMode.HUMAN_ONLY

    if is_human_only:
        # Contradiction keys on KEY PRESENCE — even an empty-valued
        # `AI-Provider:`/`AI-Tool:` line next to Human-Only is a
        # contradictory declaration, never a clean human record
        # (ADR-005; gate M-03).
        if {"ai-provider", "ai-tool"} & group.present:
            return None, [ParseWarning("contradictory-group", "ai-mode")]
        return _build_human_spec(values)

    if not has_anchor:
        anchor_key = next(iter(values), None) or next(iter(sorted(group.present)))
        return None, [ParseWarning("incomplete-group", anchor_key)]

    return _build_ai_spec(values, provider_raw_value, tool_raw_value, tool_resolved)


def _build_human_spec(group: dict[str, str]) -> tuple[ParticipationSpec, list[ParseWarning]]:
    """AI-Mode: Human-Only with no AI provider/tool anchor → one HUMAN spec,
    all six identity fields None (schema.md section 2)."""
    warnings: list[ParseWarning] = []
    roles, role_warnings = _parse_roles(group.get("ai-role"))
    warnings.extend(role_warnings)
    human_reviewed, reviewed_warning = _parse_reviewed_by(group.get("ai-reviewed-by"))
    if reviewed_warning is not None:
        warnings.append(reviewed_warning)

    spec = ParticipationSpec(
        actor_type=ActorType.HUMAN,
        provider=None,
        provider_raw=None,
        model=None,
        model_raw=None,
        tool=None,
        tool_raw=None,
        roles=roles,
        contribution_mode=ContributionMode.HUMAN_ONLY,
        human_reviewed=human_reviewed,
        source=ProvenanceSource(
            source_type=SourceType.GIT_TRAILER,
            evidence_level=EvidenceLevel.DECLARED,
            source_reference="ai-mode",
        ),
    )
    return spec, warnings


def _build_ai_spec(
    group: dict[str, str],
    provider_raw_value: str | None,
    tool_raw_value: str | None,
    tool_resolved: tuple[str, str] | None,
) -> tuple[ParticipationSpec, list[ParseWarning]]:
    """A group anchored by AI-Provider and/or a resolvable AI-Tool → one AI
    spec (schema.md section 10 normalization; explicit AI-Provider always
    wins the provider fields over a tool's owning provider)."""
    warnings: list[ParseWarning] = []

    if provider_raw_value is not None:
        provider = normalize_provider(provider_raw_value)
        provider_raw = provider_raw_value
    elif tool_resolved is not None:
        provider = tool_resolved[1]
        provider_raw = None
    else:
        provider = None
        provider_raw = None

    if tool_raw_value is not None:
        tool = tool_resolved[0] if tool_resolved is not None else None
        tool_raw = tool_raw_value
    else:
        tool = None
        tool_raw = None

    model_raw_value = group.get("ai-model")
    if model_raw_value is not None:
        model = model_raw_value.strip().lower()
        model_raw = model_raw_value
    else:
        model = None
        model_raw = None

    roles, role_warnings = _parse_roles(group.get("ai-role"))
    warnings.extend(role_warnings)

    mode_raw_value = group.get("ai-mode")
    mode: ContributionMode | None = None
    if mode_raw_value is not None:
        mode = _normalize_mode(mode_raw_value)
        if mode is None:
            warnings.append(ParseWarning("malformed-mode", "ai-mode", local_detail=mode_raw_value))

    human_reviewed, reviewed_warning = _parse_reviewed_by(group.get("ai-reviewed-by"))
    if reviewed_warning is not None:
        warnings.append(reviewed_warning)

    source_reference = "ai-provider" if "ai-provider" in group else "ai-tool"
    spec = ParticipationSpec(
        actor_type=ActorType.AI,
        provider=provider,
        provider_raw=provider_raw,
        model=model,
        model_raw=model_raw,
        tool=tool,
        tool_raw=tool_raw,
        roles=roles,
        contribution_mode=mode,
        human_reviewed=human_reviewed,
        source=ProvenanceSource(
            source_type=SourceType.GIT_TRAILER,
            evidence_level=EvidenceLevel.DECLARED,
            source_reference=source_reference,
        ),
    )
    return spec, warnings


def _normalize_mode(raw: str) -> ContributionMode | None:
    """Lowercase, '-'/' ' -> '_', then ContributionMode lookup; None when the
    normalized token is not a recognized mode (docstring contract)."""
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return ContributionMode(normalized)
    except ValueError:
        return None


def _parse_roles(raw: str | None) -> tuple[tuple[Role, ...], list[ParseWarning]]:
    """Comma-separated AI-Role tokens → Role vocabulary; unknown tokens are
    dropped with an `unknown-role` warning; missing key or empty result is
    `()` (docstring contract)."""
    if raw is None:
        return (), []
    warnings: list[ParseWarning] = []
    roles: list[Role] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            role = Role(token.lower())
        except ValueError:
            warnings.append(ParseWarning("unknown-role", "ai-role", local_detail=token))
            continue
        roles.append(role)
    return tuple(roles), warnings


def _parse_reviewed_by(raw: str | None) -> tuple[bool | None, ParseWarning | None]:
    """"human" -> True, "none" -> False, anything else -> None + a
    `malformed-reviewed-by` warning; a missing key -> None with no warning
    (docstring contract)."""
    if raw is None:
        return None, None
    normalized = raw.strip().lower()
    if normalized == "human":
        return True, None
    if normalized == "none":
        return False, None
    return None, ParseWarning("malformed-reviewed-by", "ai-reviewed-by", local_detail=raw)


#: "Name <email>", tolerant of extra spaces around the name and brackets.
_COAUTHOR_RE = re.compile(r"^\s*(?P<name>.*?)\s*<\s*(?P<email>[^<>\s]+)\s*>\s*$")


def _parse_coauthor(value: str) -> ParticipationSpec | None:
    """"Name <email>" -> AI spec via registry.match_coauthor; a malformed
    shape (no "<email>") or no registry match is silently ignored
    (docstring contract; ADR-013)."""
    match = _COAUTHOR_RE.match(value)
    if match is None:
        return None
    name = match.group("name").strip()
    email = match.group("email").strip()
    identity = match_coauthor(name, email)
    if identity is None:
        return None

    return ParticipationSpec(
        actor_type=ActorType.AI,
        provider=identity.provider,
        provider_raw=name,
        model=None,
        model_raw=None,
        tool=identity.tool,
        tool_raw=None,
        roles=(),
        contribution_mode=None,
        human_reviewed=None,
        source=ProvenanceSource(
            source_type=SourceType.GIT_TRAILER_COAUTHOR,
            evidence_level=EvidenceLevel.DECLARED,
            source_reference=COAUTHOR_KEY,
        ),
    )
