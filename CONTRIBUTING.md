# Contributing

Thanks for considering a contribution. This project is small on purpose;
the bar is correctness and privacy, not feature count.

## Setup and verification

```bash
python -m pip install -e ".[dev]"  # Python >= 3.11, git >= 2.17 (SHA-1 repos)
python -m pytest tests -p no:cacheprovider
python -m ruff check src tests scripts
python scripts/check_readme_parity.py
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
- Deterministic rendering: snapshot updates must be intentional. Regenerate
  the summary family with `python tests/unit/test_render_summary.py` and the
  heatmap/badge family with `python tests/unit/test_heatmap_svg.py`. These
  sanctioned commands also update the corresponding committed samples in
  `docs/assets/`; never hand-edit or copy snapshots or samples.
- Packaging or release changes must also pass the artifact and clean-wheel
  checks in [docs/RELEASING.md](docs/RELEASING.md).

## Reporting privacy/security issues

Follow [SECURITY.md](SECURITY.md) and use GitHub's private vulnerability
reporting. Do not disclose sensitive details in a public issue.
