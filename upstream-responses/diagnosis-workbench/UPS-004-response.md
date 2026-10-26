# Response to UPS-004: Appendix findings tables always show only Fail / Partial / Needs Review

| | |
|---|---|
| Verdict | **Valid enhancement. Implemented as a configurable status list; default unchanged.** |
| Fixed in | `dataiku-diagnosis-toolkit` 0.38.17, bundling `dataiku-review-generator` 0.10.10 |
| Files changed | `scripts/build_deck_v2.py`, `config/deck_layout.yaml`, `README.md`, `tests/test_deck_v2.py`, `CHANGELOG.md` (in `mcp-server-review-generator/`) |
| Reviewed | 2026-10-26, against v0.38.15 (`f099053`) |

## What was checked

The description is accurate: `detail_slides` held the status filter, its sort order and the title wording as literals.
The three-status default was deliberate (a Pass row has no action), so it stays the default.

## What changed

```yaml
v2:
  detail_statuses: [Fail, Partial, "Needs Review"]   # the default; any of Fail, Partial, Needs Review, Pass
```

- Omitted, the key gives today's decks unchanged (tests compare the default and the explicit default).
- Rows stay in severity order (Fail, Partial, Needs Review, Pass) whatever order the list is written in. The slide
  title counts follow the same list ("2 needs review, 1 pass").
- Pass rows show the item's headline and evidence in Finding and `-` in Action.
- `[]` builds no findings tables, and the deck still validates.
- A list that is not a list, or holds an unknown status (including `Not Applicable`, which keeps its own slide), is
  rejected with a message naming `v2.detail_statuses`.
- Applies to the branded and standard decks alike. The "Passed checks" slide is unchanged.

## Answers to your open questions

- **Pass rows in this table?** Yes, opt-in. The Passed checks slide keeps listing them either way.
- **Empty list?** Allowed. The build adds a warning (`warnings` in the result) when `Needs Review` is not in the list
  and Needs Review items exist, since those rows would otherwise have no appendix entry.
- **Per-status or on/off?** Per-status, as proposed.

## Not verified

The slide-count growth for a large checklist with Pass included was not measured; the packing logic is the existing one
and the row cap (`detail_max_rows`) still applies. `validate_deck` has no reference to these tables and passes for
the empty list and the default.

## What the workbench needs to do on adopting 0.38.17

Bump the pin, set UPS-004 to "fixed in 0.38.17", and write the reviewer's choice into `v2.detail_statuses` in the
config it supplies, the way it does `v2.standard_theme`. Surface the build's new warning if the list omits Needs Review.
