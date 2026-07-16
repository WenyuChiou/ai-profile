# Contributing

Thanks for considering a contribution. This project is small on purpose;
the bar is correctness and privacy, not feature count.

## Setup and verification

```bash
pip install -e ".[dev]"        # Python >= 3.11, git >= 2.17 (SHA-1 repos)
python -m pytest               # full suite must pass (states its count)
python -m ruff check src tests
```

Integration tests build throwaway git repositories under pytest tmp dirs;
no network is used anywhere in the suite, ever.

## Ground rules

- `docs/schema.md` is the normative event contract; `docs/architecture.md`
  pins module boundaries (renderers/exporters consume `VizStats` only).
  Where code and docs disagree, the docs win and the code is a bug.
- **Contract changes require an ADR** under `docs/decisions/` (and a schema
  version bump per ADR-012). New sections in existing docs get review.
- **Registry additions need primary evidence**: an entry in
  `src/aiprofile/registry.py` must cite an official doc, tool source code,
  or verified real-commit usage (see `docs/landscape.md` §2.1 for the
  verification standard). Unverified strings stay out.
- **Attribution is explicit-evidence-only.** No code-style inference, no
  LLM classification of historical commits — patches adding either will be
  declined regardless of accuracy.
- Privacy invariants are test-enforced (leak tests, policy tests); a change
  that weakens `VizStats`' structural redaction needs its own ADR and a
  very good reason. Read `docs/PRIVACY.md` first.
- Deterministic rendering: snapshot updates must be intentional; regenerate
  via `python tests/unit/test_render_summary.py` and inspect the diff. That
  one command regenerates BOTH the test snapshots and the committed README
  sample assets (`docs/assets/summary-sample-{light,dark}.svg`) from their
  authoritative synthetic fixture — never hand-edit or copy either set; a
  byte-exact drift guard fails the suite if they fall out of sync.

## Reporting privacy/security issues

Open an issue titled "privacy report" without including the sensitive
details, and the maintainer will follow up privately.
