## Summary

Describe the user-visible outcome and why the change belongs in the current
scope.

## Contract impact

- [ ] No ACE schema, aggregation-unit, attribution, privacy-boundary, or CLI
      contract change.
- [ ] If a contract changed, the required ADR and schema/version update are
      included.
- [ ] No public claim is stronger than the code and tests guarantee.

## Verification

- [ ] `python -m pytest tests -p no:cacheprovider`
- [ ] `python -m ruff check src tests scripts`
- [ ] Snapshot families regenerated only with their sanctioned commands, or
      not affected.
- [ ] Privacy canaries checked when public output changed.
- [ ] Wheel/sdist contract and clean-wheel smoke checked when packaging or
      release code changed.

State the observed test count and paste the final command lines:

## Screenshots or artifacts

For visual changes, include light/dark and narrow/wide evidence. Do not attach
private repository data.
