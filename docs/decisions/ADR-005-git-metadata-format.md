# ADR-005: Git metadata format (the ACE trailer convention)

Status: accepted (2026-07-14)

## Context

Trailers are the portable, visible attribution channel (proposal §8). We
must pin exact keys, a multi-participation grouping rule, and how commits
are read, so the parser (WP-B) is implementable without judgment calls.

## Decision

Recognized trailer keys (case-insensitive match):

```text
AI-Provider   raw provider name → registry normalization
AI-Model      raw model name → registry normalization
AI-Tool       raw tool name → registry normalization
AI-Role       comma-separated role list → vocabulary (unknown tokens
              dropped with a warning; never invented)
AI-Mode       contribution mode → vocabulary (unparseable → null + warning)
AI-Reviewed-By  "human" → true, "none" → false, anything else → null + warning
AI-Schema     informational (logged; parsing does not depend on it)
```

Grouping rule for multiple participations in one commit (deterministic,
order-based): iterate `AI-*` trailers in message order; a group collects
key→value pairs; when a key already present in the current group repeats, a
new group starts. A group yields an AI participation only if `AI-Provider`
is present or `AI-Tool` resolves to a provider via the registry. Two
carved exceptions (Phase 0 review):

- a group declaring `AI-Mode: Human-Only` with **no** AI provider/tool
  yields a **human** participation (null provider/tool, evidence
  `declared`) — the v0.1 producer of the `human` category (schema.md §2);
- a group declaring `AI-Mode: Human-Only` **and** an AI provider/tool is
  contradictory and is discarded with a warning.

Any other group lacking a resolvable provider is discarded with a warning
(no invention).

Additionally recognized: `Co-authored-by: Name <email>` matching the
known-AI identity registry — exact email match, plus a display-name-prefix
condition where the entry specifies one (ADR-013) →
`git_trailer_coauthor` participation (this is how Claude Code commits are
attributed in the wild). Unmatched co-authors are ignored.

Commit reading: a single `git log HEAD` pass per repository with
`--pretty=format:` using `%x1e`/`%x1f` separators and
`%(trailers:only,unfold)` — git's own trailer parser, not a
reimplementation. This is the portable boolean-bare form (git ≥ 2.17;
validated byte-identical to the `only=true` spelling on git 2.47.1);
minimum supported git is pinned at 2.17. Both trailer sources are
`evidence_level: declared` (unverified commit-message text either way).

Git Notes are out of v0.1 (namespace reserved in ADR-006).

## Consequences

- Attribution is portable, human-visible, and survives clones/forges.
- Anything expressible only in richer structures waits for Notes.
- The grouping rule is convention; foreign commits using a different
  multi-AI convention may parse as one merged group — documented limitation.
