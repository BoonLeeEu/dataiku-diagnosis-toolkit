# Response to UPS-002: Standard deck uses Dataiku's palette and font

| | |
|---|---|
| Verdict | **Valid observation. Not a bug. No change made.** |
| Status | Open, waiting on a design decision from the toolkit owner |
| Reviewed | 2026-10-25, against v0.38.13 (`5b39adb`) |

## What was checked

Everything the issue states about the code is accurate: `DK`, `MINT`, `BG`, `PALE` and the dependent `STATUS`,
`SEG` and `DOT` tables are module-level constants in `build_deck_v2.py`; `P(..., font="Roboto")` and
`style_standard_title` hard-code Roboto; `Deck(prs, standard=...)` switches layout and title styling only.
`build_standard_base`'s docstring says the base keeps "the v2 palette", so the look is deliberate, as the issue
itself notes.

## Why nothing was changed

- It is an enhancement. Both suggested options change what a customer-facing deck looks like, or add a configuration
  surface, and neither is a correction.
- The toolkit's stated priority for the standard deck is a usable fallback with no brand claim. Whether a fallback
  should *look different* from the branded deck is a product call the owner has not made.
- A new default palette would change every standard deck produced by every caller, including ones relying on the
  current look, and would need golden updates in `tests/test_golden_deck.py`.

## Recommendation, if the owner decides to act

Option 2 from the issue (a `v2.standard_theme:` block in `config/deck_layout.yaml`, defaulting to today's values) is
the safest: output is unchanged for everyone who does nothing, and the workbench could set its indigo/Arial theme in
config instead of rewriting XML. It needs the `STATUS`/`SEG`/`DOT` tables built when the theme is resolved rather than
at import. Keep the status colours (pass, fail, partial, review) fixed so their meaning never shifts.

## Answers to the open questions

- **Is "standard looks like branded" intended?** Yes, for now, with the cover note as the signal.
- **Is the cover note enough?** Undecided. This is the question for the owner.
- **How to expose a theme?** Undecided; config (option 2) is the leading candidate.

## Effect on the workaround

None. `apply_unbranded_theme` keeps working because the swapped values are unchanged. Keep recording it in the
workbench's drift checklist.
