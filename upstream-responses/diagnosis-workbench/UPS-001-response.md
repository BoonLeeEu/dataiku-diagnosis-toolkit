# Response to UPS-001: Standard deck is rejected by Keynote

| | |
|---|---|
| Verdict | **Valid. Fixed.** |
| Fixed in | `dataiku-diagnosis-toolkit` 0.38.14, bundling `dataiku-review-generator` 0.10.7 |
| Files changed | `scripts/build_deck_v2.py`, `scripts/validate_deck.py`, `tests/test_standard_deck.py` (in `mcp-server-review-generator/`) |
| Reviewed | 2026-10-25, against v0.38.13 (`5b39adb`) |

## What was checked

Reproduced on this machine (macOS, Python 3.x, python-pptx 1.0.2), building a standard deck from the toolkit's
synthetic checklist helper with the unfixed code:

- `ppt/presentation.xml` has no `<p:notesMasterIdLst>`, although a notes master part exists. Confirmed.
- `<p:sldSz cx="9144000" cy="5143500" type="screen4x3"/>`: a 16:9 page labelled 4:3. Confirmed.
- `validate_deck.validate()` returned `[]` for it. Confirmed, which is the false assurance the issue describes.

Your root cause and line references matched the code (`build_deck_v2.py:673` notes, `build_standard_base` using
python-pptx's 4:3 default template).

**Not verified here:** Keynote itself. I could not run it, so "Keynote now opens the file" rests on your variant
table (v4/v5 open) plus the fixed file matching v4's structure, not on a Keynote run of the new build. Please confirm
with one real file after adopting 0.38.14.

## What changed

1. `declare_notes_master(prs)` in `build_deck_v2.py` finds the `notesMaster` relationship and inserts
   `<p:notesMasterIdLst><p:notesMasterId r:id="…"/></p:notesMasterIdLst>` directly after `</p:sldMasterIdLst>`
   (the ECMA-376 order). It runs just before the final `prs.save`, after the last notes slide exists. It does nothing
   if the element is already there or there is no notes master, so it is idempotent.
2. `clear_stale_size_type(prs)` removes `type="screen4x3"` from `sldSz` in `build_standard_base` after the resize,
   but only when the page is not 4:3.
3. `validate_deck.validate()` has two new checks (your suggested fix item 3): a notes master part without the
   declaration, and `screen4x3` on a page that is not 4:3.
4. Tests (your item 4):
   - `test_regression_v0_10_7_standard_deck_declares_notes_master` builds a standard deck and asserts one
     `notesMasterIdLst`, in the right element order, no `screen4x3`, and a clean validation.
   - `test_validate_flags_undeclared_notes_master_and_stale_size_label` disables both fixes and asserts the validator
     reports each.

## Answers to the open questions

- **Do template-based (branded) decks hit it?** No. Built with the real Dataiku Branding Template 2026, the branded
  deck already has `<p:notesMasterIdLst>` and no `screen4x3`, and validates clean with the fix disabled. Only the
  standard deck was affected.
- **Should `validate_deck` carry a "strict reader" list?** Yes, started: the two checks above. It cannot render, so
  the list stays a set of specific, structural rules added when a real viewer rejects a real file, not a general
  conformance check.

## Effect on the workaround

`deck_postprocess.fix_presentation` becomes a no-op on decks from 0.38.14 or later. Keeping it is harmless. The
integration test asserting the result on a freshly built standard deck should still pass, and now exercises upstream's
fix instead of yours.

## Notes

- The `app.xml` "On-screen Show (4:3)" label and the `printerSettings1.bin` part from your variants v1/v2 were not
  changed. Your table shows they were not what made Keynote reject the file.
- Only the v2 deck is affected. The v1 style builds from the branding master and was not touched.
