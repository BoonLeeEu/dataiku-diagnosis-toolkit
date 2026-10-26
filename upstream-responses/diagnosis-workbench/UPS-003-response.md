# Response to UPS-003: Rule-derived Risk 2 slide picks a different section on different runs

| | |
|---|---|
| Verdict | **Valid bug. Fixed.** |
| Fixed in | `dataiku-diagnosis-toolkit` 0.38.16, bundling `dataiku-review-generator` 0.10.9 |
| Files changed | `scripts/build_deck_v2.py`, `tests/test_deck_v2.py`, `CHANGELOG.md` (in `mcp-server-review-generator/`) |
| Reviewed | 2026-10-26, against v0.38.15 (`f099053`) |

## What was checked

The root cause is accurate: `risk2_slide` took `max()` over a set of section-name strings, so equal failure counts were
resolved by hash-dependent set order. Your table (different titles for `PYTHONHASHSEED` 0, 1, 3) follows from that.

Your open question about other set-iteration choices: `deck_analysis.root_cause_groups` (the set-returning helper near
line 116 you flagged) builds groups from dicts and lists and sorts them by `(-len, first id)`, so it is deterministic.
No other visible choice in `build_deck_v2.py` depends on set order. The checklist-review skill was not audited.

## What changed

New `risk2_section(fails, order)` returns the section with the most failures. A tie goes to the section earliest in
`a.section_order` (checklist order); a section missing from the order ranks last. `risk2_slide` calls it. The output for
inputs without a tie is unchanged.

Answer to your open question: earliest in checklist order. It needs no new policy, and the narrative's `risk2` is the
place to override it.

Test: `test_risk2_section_tie_goes_to_the_earliest_section` covers ties under two orderings and a non-tie. It is
independent of the hash seed by construction; the suite also passes under `PYTHONHASHSEED` 0, 1 and 3.

## What the workbench needs to do on adopting 0.38.16

Bump the pin, set UPS-003 to "fixed in 0.38.16", and drop the Risk 2 title normalisation in
`test_pinned_toolkit_deck_follows_the_slide_arrangement` (it is harmless to keep).
