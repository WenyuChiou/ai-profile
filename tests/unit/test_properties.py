"""Generative, randomized property tests (ROADMAP "property-based unit-
invariant fuzzing", gate-2 section 14).

These complement the FIXED-permutation tests in test_schema_event.py
(test_merge_is_permutation_invariant,
test_group_merge_exhaustive_permutations_of_four_leaves) with hypothesis-
generated, shrinking, randomized inputs across four invariant families
derived from docs/schema.md (docs win over code, per AGENTS.md /
CONTRIBUTING.md):

  a. Trailer parsing (docs/schema.md section 5, ADR-005; adapters/
     trailers.py docstring) -- parse_commit_trailers never raises, the
     spec count is bounded, and every spec satisfies the field contracts
     documented on ParticipationSpec / build_event.
  b. Merge purity (docs/schema.md section 8.3, ADR-008) -- merging any
     permutation of the SAME leaf multiset yields byte-identical
     canonical output.
  c. Dedup/identity (docs/schema.md section 8.1/8.2) -- identical
     identity fields collapse to one event_id; any single identity field
     change yields a different event_id; non-identity fields (model,
     roles, ...) never affect it.
  d. Evidence ordering (docs/schema.md section 6.1) -- evidence_level is
     always the MAXIMUM precedence over the event's provenance sources,
     both at construction and after a merge.

Determinism (repo values deterministic suites, CONTRIBUTING.md): every
test below is decorated with a SHARED settings object using
derandomize=True (hypothesis replaces its random source with a
per-test-id deterministic PRNG instead of external randomness/database
state) and deadline=None (pure in-memory functions; no reason to time
box them, and a loaded CI box should never flake on wall-clock). This
makes re-runs on the same hypothesis version reproduce the same
examples on this machine and in CI alike. max_examples is bounded to
keep the suite fast.

Windows/cp950 note: every generated string in this file is restricted
to an explicit ASCII alphabet (see _ASCII_ALPHABET) so a shrunk
counterexample dumped to a cp950 console can never contain a
non-encodable character.
"""

from __future__ import annotations

import itertools
import string

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from aiprofile.adapters.trailers import AI_TRAILER_KEYS, parse_commit_trailers
from aiprofile.registry import COAUTHOR_IDENTITIES, PROVIDER_ALIASES, TOOL_ALIASES
from aiprofile.schema.event import (
    ProvenanceSource,
    build_event,
    canonical_json,
    merge_event_group,
)
from aiprofile.schema.vocab import (
    ALLOWED_SOURCE_REFERENCES,
    CANONICAL_PROVIDERS,
    CANONICAL_TOOLS,
    EVIDENCE_PRECEDENCE,
    ActorType,
    ContributionMode,
    EvidenceLevel,
    Role,
    SourceType,
)

# ---------------------------------------------------------------------------
# Shared settings: bounded, deterministic (see module docstring).
# ---------------------------------------------------------------------------

slow_settings = settings(derandomize=True, deadline=None, max_examples=100)

FIXED_TS = "2026-01-01T00:00:00+00:00"

_ASCII_ALPHABET = string.ascii_letters + string.digits + "-_. "

_ascii_text = st.text(alphabet=_ASCII_ALPHABET, min_size=0, max_size=20)
_ascii_text_nonempty = st.text(alphabet=_ASCII_ALPHABET, min_size=1, max_size=20)
_hex40 = st.text(alphabet="0123456789abcdef", min_size=40, max_size=40)


@st.composite
def _iso_timestamps(draw):
    """Offset-aware ISO 8601 strings only (build_event rejects naive/date-
    only forms per docs/schema.md and test_h05_*_rejected)."""
    year = draw(st.integers(min_value=2000, max_value=2099))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    offset_minutes = draw(st.sampled_from([-720, -480, -60, 0, 60, 330, 480, 540, 840]))
    sign = "+" if offset_minutes >= 0 else "-"
    oh, om = divmod(abs(offset_minutes), 60)
    return (
        f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"
        f"{sign}{oh:02d}:{om:02d}"
    )


def _source_strategy():
    """A single ProvenanceSource valid per schema.md 6.2 (source_reference
    enum-constrained per source type)."""

    def one(source_type: SourceType):
        refs = sorted(r for r in ALLOWED_SOURCE_REFERENCES[source_type] if r is not None)
        return st.builds(
            ProvenanceSource,
            source_type=st.just(source_type),
            evidence_level=st.sampled_from(list(EvidenceLevel)),
            source_reference=st.sampled_from(refs),
        )

    return st.one_of(one(SourceType.GIT_TRAILER), one(SourceType.GIT_TRAILER_COAUTHOR))


_sources_list = st.lists(_source_strategy(), min_size=1, max_size=4)


# ===========================================================================
# (a) Trailer parsing invariants (docs/schema.md section 5; ADR-005)
# ===========================================================================

# Value strategies per AI-* key: a mix of registry-recognized values (real
# vocab), unrecognized garbage, and empty strings (the "present but
# valueless" edge that matters to the Human-Only contradiction rule --
# gate M-03), plus deliberately unknown roles/modes per the task brief.
_PROVIDER_VALUES = st.one_of(
    st.sampled_from(sorted(PROVIDER_ALIASES) or ["anthropic"]),
    st.sampled_from(["anthropic", "OpenAI", "Google", "not-a-real-vendor", "Qorvax-9"]),
    _ascii_text,
)
_TOOL_VALUES = st.one_of(
    st.sampled_from(sorted(TOOL_ALIASES) or ["claude-code"]),
    st.sampled_from(["claude-code", "codex-cli", "not-a-real-tool", "Zylex-99"]),
    _ascii_text,
)
_ROLE_TOKEN = st.sampled_from([r.value for r in Role] + ["unknown-role-token", "banana", ""])
_ROLE_VALUES = st.lists(_ROLE_TOKEN, min_size=0, max_size=4).map(lambda ts: ",".join(ts))
_MODE_VALUES = st.one_of(
    st.sampled_from([m.value for m in ContributionMode]),
    st.sampled_from(["AI-Assisted", "ai assisted", "Human-Only", "not-a-real-mode", ""]),
    _ascii_text,
)
_REVIEWED_BY_VALUES = st.sampled_from(["human", "Human", "none", "None", "somebody-else", ""])
_SCHEMA_VALUES = _ascii_text  # informational only per docstring contract

_VALUE_STRATEGY_BY_KEY = {
    "ai-provider": _PROVIDER_VALUES,
    "ai-model": _ascii_text,
    "ai-tool": _TOOL_VALUES,
    "ai-role": _ROLE_VALUES,
    "ai-mode": _MODE_VALUES,
    "ai-reviewed-by": _REVIEWED_BY_VALUES,
    "ai-schema": _SCHEMA_VALUES,
}


@st.composite
def _ai_trailer_group_lines(draw):
    """One 'logical' AI-* trailer group: a set of DISTINCT trailer keys
    (no internal repeats) rendered as 'Key: value' lines in random casing
    and shuffled order.

    Why this bounds the parser's actual group count (used by the test
    below): the parser only starts a NEW group when it sees a key that is
    ALREADY present in the currently-open group with a non-empty value
    (ADR-005). A chunk with no internally-repeated key can therefore
    trigger AT MOST one such split relative to whatever preceded it --
    concatenating N of these chunks (in ANY order, interleaved with
    anything that isn't an AI-* key) can never yield MORE than N actual
    groups, only fewer (when two chunks happen to share no repeated key
    and merge). So len(specs) <= (number of chunks) + (number of
    co-author lines) is a true upper bound regardless of shuffling --
    verified by construction here, not by re-deriving the grouping
    algorithm.
    """
    keys = draw(
        st.lists(
            st.sampled_from(sorted(AI_TRAILER_KEYS)),
            min_size=1,
            max_size=len(AI_TRAILER_KEYS),
            unique=True,
        )
    )
    lines = []
    for key in keys:
        value = draw(_VALUE_STRATEGY_BY_KEY[key])
        rendered_key = draw(st.sampled_from([key, key.upper(), key.title()]))
        lines.append(f"{rendered_key}: {value}")
    rng = draw(st.randoms())
    rng.shuffle(lines)
    return lines


@st.composite
def _trailer_block(draw):
    """A whole commit trailer block: N logical AI-* groups + M co-author
    lines + a few non-trailer junk lines, all interleaved. Returns
    (lines, n_groups, n_coauthor_lines)."""
    n_groups = draw(st.integers(min_value=0, max_value=4))
    group_chunks = [draw(_ai_trailer_group_lines()) for _ in range(n_groups)]

    n_coauthor = draw(st.integers(min_value=0, max_value=3))
    coauthor_chunks = []
    known_emails = sorted(COAUTHOR_IDENTITIES) or ["noreply@anthropic.com"]
    for _ in range(n_coauthor):
        email = draw(st.sampled_from(known_emails + ["nobody@example.com", "x@y.test"]))
        name = draw(_ascii_text_nonempty)
        coauthor_chunks.append([f"Co-authored-by: {name} <{email}>"])

    chunks = group_chunks + coauthor_chunks
    order = draw(st.permutations(list(range(len(chunks))))) if chunks else []
    lines: list[str] = []
    for idx in order:
        lines.extend(chunks[idx])

    n_junk = draw(st.integers(min_value=0, max_value=2))
    for _ in range(n_junk):
        junk = draw(_ascii_text)  # no ':' guaranteed only if we strip colons
        junk = junk.replace(":", "")
        pos = draw(st.integers(min_value=0, max_value=len(lines)))
        lines.insert(pos, junk)

    return lines, n_groups, n_coauthor


@slow_settings
@given(block=_trailer_block())
def test_trailer_parsing_never_raises_and_respects_spec_count_bound(block):
    lines, n_groups, n_coauthor = block
    specs, warnings = parse_commit_trailers(lines)  # must never raise

    assert len(specs) <= n_groups + n_coauthor


@slow_settings
@given(block=_trailer_block())
def test_trailer_parsing_specs_satisfy_field_contracts_and_rebuild(block):
    """Every spec parse_commit_trailers returns satisfies its documented
    field contract (ParticipationSpec docstring) AND round-trips through
    build_event without raising -- the exact use the scanner makes of it
    (docs/schema.md section 1; adapters/trailers.py module docstring:
    'the scanner turns specs into validated ACE events')."""
    lines, _n_groups, _n_coauthor = block
    specs, _warnings = parse_commit_trailers(lines)

    for spec in specs:
        if spec.actor_type is ActorType.HUMAN:
            assert spec.provider is None
            assert spec.provider_raw is None
            assert spec.model is None
            assert spec.model_raw is None
            assert spec.tool is None
            assert spec.tool_raw is None
            assert spec.contribution_mode is ContributionMode.HUMAN_ONLY
        elif spec.actor_type is ActorType.AI:
            assert spec.provider is None or spec.provider in CANONICAL_PROVIDERS
            assert spec.tool is None or spec.tool in CANONICAL_TOOLS
            assert spec.provider or spec.provider_raw or spec.tool or spec.tool_raw
            if spec.model_raw is not None:
                assert spec.model == spec.model_raw.strip().lower()
            else:
                assert spec.model is None
        else:
            raise AssertionError(f"unexpected actor_type from trailer parse: {spec.actor_type}")

        assert spec.contribution_mode is None or isinstance(
            spec.contribution_mode, ContributionMode
        )
        assert spec.human_reviewed is None or isinstance(spec.human_reviewed, bool)
        for role in spec.roles:
            assert isinstance(role, Role)

        src = spec.source
        assert src.source_type in (SourceType.GIT_TRAILER, SourceType.GIT_TRAILER_COAUTHOR)
        assert src.evidence_level is EvidenceLevel.DECLARED
        assert src.source_reference in ALLOWED_SOURCE_REFERENCES[src.source_type]

        # Round-trip through build_event exactly as the scanner does
        # (test_schema_event.py's _leaf_from_spec pattern) -- must never
        # raise SchemaValidationError.
        event = build_event(
            actor_type=spec.actor_type,
            provider=spec.provider,
            provider_raw=spec.provider_raw,
            model=spec.model,
            model_raw=spec.model_raw,
            tool=spec.tool,
            tool_raw=spec.tool_raw,
            roles=spec.roles,
            contribution_mode=spec.contribution_mode,
            human_reviewed=spec.human_reviewed,
            timestamp=FIXED_TS,
            repository_uid="remote:v5:github.com/x/y",
            commit_sha="f" * 40,
            sources=[spec.source],
        )
        assert event.evidence_level is EvidenceLevel.DECLARED


# ===========================================================================
# (b) Merge purity (docs/schema.md section 8.3, ADR-008)
# ===========================================================================


@st.composite
def _ai_leaf_group(draw):
    """N (2..4) leaf AceEvents sharing one identity (same provider, tool,
    repository_uid, commit_sha, actor_type=ai) but varying every OTHER
    field -- generalizes the fixed 3/4-leaf permutation tests in
    test_schema_event.py to randomized field values."""
    provider = draw(st.sampled_from(sorted(CANONICAL_PROVIDERS)))
    tool = draw(st.one_of(st.none(), st.sampled_from(sorted(CANONICAL_TOOLS))))
    repo = draw(_ascii_text_nonempty)
    sha = draw(_hex40)
    n = draw(st.integers(min_value=2, max_value=4))

    events = []
    for _ in range(n):
        model_raw = draw(st.one_of(st.none(), _ascii_text_nonempty))
        roles = draw(st.lists(st.sampled_from(list(Role)), max_size=3))
        mode = draw(st.one_of(st.none(), st.sampled_from(list(ContributionMode))))
        reviewed = draw(st.one_of(st.none(), st.booleans()))
        ts = draw(_iso_timestamps())
        recorded = draw(st.one_of(st.none(), _iso_timestamps()))
        sources = draw(_sources_list)
        events.append(
            build_event(
                actor_type=ActorType.AI,
                provider=provider,
                tool=tool,
                repository_uid=repo,
                commit_sha=sha,
                timestamp=ts,
                model=model_raw.lower() if model_raw is not None else None,
                model_raw=model_raw,
                roles=roles,
                contribution_mode=mode,
                human_reviewed=reviewed,
                sources=sources,
                recorded_at=recorded,
            )
        )
    return events


@slow_settings
@given(leaves=_ai_leaf_group())
def test_merge_permutation_purity_generative(leaves):
    """G2-06 generalized: ALL permutations of a RANDOMLY generated leaf
    set (2..4 leaves, varying model/roles/mode/reviewed/timestamp/
    sources/recorded_at) reduce to byte-identical canonical output."""
    results = {
        canonical_json(merge_event_group(list(perm))) for perm in itertools.permutations(leaves)
    }
    assert len(results) == 1

    # (d) evidence ordering also holds across the merge: the merged
    # evidence level is the max precedence over the UNION of every leaf's
    # OWN sources (computed independently of the SUT's merged.sources so
    # this isn't just re-checking the SUT against itself).
    merged = merge_event_group(leaves)
    expected = max(EVIDENCE_PRECEDENCE[s.evidence_level] for e in leaves for s in e.sources)
    assert EVIDENCE_PRECEDENCE[merged.evidence_level] == expected


# ===========================================================================
# (c) Dedup / identity (docs/schema.md section 8.1, 8.2)
# ===========================================================================


@slow_settings
@given(
    repo=_ascii_text_nonempty,
    sha=_hex40,
    provider=st.sampled_from(sorted(CANONICAL_PROVIDERS)),
    tool=st.one_of(st.none(), st.sampled_from(sorted(CANONICAL_TOOLS))),
    model_a=_ascii_text_nonempty,
    model_b=_ascii_text_nonempty,
    roles_a=st.lists(st.sampled_from(list(Role)), max_size=3),
    roles_b=st.lists(st.sampled_from(list(Role)), max_size=3),
)
def test_identical_identity_fields_dedup_to_one_event_id(
    repo, sha, provider, tool, model_a, model_b, roles_a, roles_b
):
    """docs/schema.md 8.2: model and roles are DELIBERATELY excluded from
    identity, so two events differing ONLY in those fields must share one
    event_id -- the fixed counterpart of test_h... regressions, fuzzed."""
    base = dict(
        actor_type=ActorType.AI,
        repository_uid=repo,
        commit_sha=sha,
        provider=provider,
        tool=tool,
        timestamp=FIXED_TS,
        sources=[ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")],
    )
    e1 = build_event(**base, model=model_a, model_raw=model_a, roles=roles_a)
    e2 = build_event(**base, model=model_b, model_raw=model_b, roles=roles_b)
    assert e1.event_id == e2.event_id


@slow_settings
@given(
    repo=_ascii_text_nonempty,
    repo2=_ascii_text_nonempty,
    sha=_hex40,
    sha2=_hex40,
    provider=st.sampled_from(sorted(CANONICAL_PROVIDERS)),
    provider2=st.sampled_from(sorted(CANONICAL_PROVIDERS)),
    tool=st.one_of(st.none(), st.sampled_from(sorted(CANONICAL_TOOLS))),
    tool2=st.one_of(st.none(), st.sampled_from(sorted(CANONICAL_TOOLS))),
)
def test_single_identity_field_change_changes_event_id(
    repo, repo2, sha, sha2, provider, provider2, tool, tool2
):
    """docs/schema.md 8.1: repository_uid, commit_sha, actor.provider,
    actor.tool are ALL load-bearing identity fields -- changing any ONE
    of them (holding the rest fixed) must change event_id."""
    assume(repo != repo2)
    assume(sha != sha2)
    assume(provider != provider2)
    assume(tool != tool2)

    base = dict(
        actor_type=ActorType.AI,
        repository_uid=repo,
        commit_sha=sha,
        provider=provider,
        tool=tool,
        timestamp=FIXED_TS,
        sources=[ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")],
    )
    base_id = build_event(**base).event_id

    for field, new_value in (
        ("repository_uid", repo2),
        ("commit_sha", sha2),
        ("provider", provider2),
        ("tool", tool2),
    ):
        mutated = dict(base)
        mutated[field] = new_value
        mutated_id = build_event(**mutated).event_id
        assert mutated_id != base_id, f"event_id did not change when {field} was mutated"


# ===========================================================================
# (d) Evidence ordering at construction time (docs/schema.md section 6.1)
# ===========================================================================


@slow_settings
@given(
    provider=st.sampled_from(sorted(CANONICAL_PROVIDERS)),
    sources=_sources_list,
)
def test_evidence_level_is_max_precedence_over_sources(provider, sources):
    """docs/schema.md 6.1: 'An event's evidence_level is the MAXIMUM over
    its provenance sources.' Computed independently from the RAW input
    list (not event.sources, which the SUT itself deduped) so this isn't
    circular: dedup-by-key always keeps the higher of two colliding
    evidence levels, so the max is invariant across that dedup."""
    event = build_event(
        actor_type=ActorType.AI,
        provider=provider,
        repository_uid="r",
        commit_sha="a" * 40,
        timestamp=FIXED_TS,
        sources=sources,
    )
    expected = max(EVIDENCE_PRECEDENCE[s.evidence_level] for s in sources)
    assert EVIDENCE_PRECEDENCE[event.evidence_level] == expected
