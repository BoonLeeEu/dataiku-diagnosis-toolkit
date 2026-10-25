# Response to UPS-002: Standard deck uses Dataiku's palette and font

| | |
|---|---|
| Verdict | **Valid enhancement. Implemented as option 2 (configurable theme).** |
| Fixed in | `dataiku-diagnosis-toolkit` 0.38.15, bundling `dataiku-review-generator` 0.10.8 |
| Files changed | `scripts/build_deck_v2.py`, `config/deck_layout.yaml`, `README.md`, `tests/test_standard_deck.py` (in `mcp-server-review-generator/`) |
| Reviewed | 2026-10-25, against v0.38.13 (`5b39adb`) |

## What was checked

The issue's description of the code is accurate: `DK`, `MINT`, `BG`, `PALE` and the dependent `STATUS`, `SEG` and
`DOT` tables are module constants in `build_deck_v2.py`, and `Roboto` was hard-coded in `P(...)` and
`style_standard_title`. The look was deliberate (the `build_standard_base` docstring says so). It was kept as the
default; the owner chose to make it configurable.

## What changed

`config/deck_layout.yaml` has a new block:

```yaml
v2:
  standard_theme:
    dark: "06312E"   # cover, dark slides, headings
    page: "FEFEF9"   # light slide background
    pale: "D6E4E2"   # text on dark backgrounds
    font: "Roboto"   # body and title font
```

- Every key is optional and defaults to the values above, so output is unchanged for anyone who does nothing.
- It applies to the standard deck only. The branded deck ignores the block, and a bad theme never breaks a branded build.
- Hex values are validated (6 digits; quote them in YAML). Unknown keys and an empty font are rejected with a message
  naming the key.
- Not themed, on purpose (your suggested fix item 1): status colours, the stacked-bar and dot colours, and the mint
  accent (`3EDAB2`), which doubles as the Pass colour. `STATUS`, `SEG` and `DOT` are therefore still built at import
  and nothing captures a themed value (your item 3 is satisfied by not theming what they use).
- Mechanism: `standard_theme(theme)` rebinds `DK`, `BG`, `PALE` and `FONT` for the duration of one build and restores
  them in a `finally`. The build is not thread-safe while a theme is applied, which matches the MCP server's
  one-build-at-a-time use.
- Tests (your item 4): defaults still produce `06312E`/`FEFEF9`/`D6E4E2`/Roboto; a configured theme appears and the
  Dataiku values do not (while `3EDAB2` stays); partial config falls back per key; bad config is rejected; module
  colours are restored after a build; a branded build never reads the theme.

## Not changed

- `Spectral` (the headline figures) and `Courier New` (setting values) are still fixed. `Spectral` is not installed on
  many machines either. If you want it themed, tell the owner and a `number_font` key can be added.
- The cover note "Standard layout (Dataiku branding template not applied)" is unchanged and still the distinguishing
  signal, now alongside a visibly different look if you configure one.
- Not verified: the result in Keynote or PowerPoint for a themed deck. The tests check the XML only.

## Answers to the open questions

- **Is "standard looks like branded" intended?** It was, and stays the default.
- **Is the cover note enough?** Left as is; the theme now gives a second signal for anyone who wants one.
- **How to expose a theme?** YAML (`v2.standard_theme`). No `build_v2` argument or MCP parameter was added.

## Effect on the workaround

To adopt: set `standard_theme` to the workbench's indigo values and `font: "Arial"` in the config it ships to the
plugin, then retire `apply_unbranded_theme`. Until then it still works, because the default values it swaps are
unchanged. If both run, the post-process finds nothing to replace and does nothing.
The workbench keeps `3EDAB2`, which matches what is left untouched.
