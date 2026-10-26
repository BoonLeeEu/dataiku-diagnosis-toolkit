# Responses to `diagnosis_workbench` upstream issues

Replies to the issue write-ups in
`github.com/boonleeeu-dataiku/diagnosis_workbench` → `code_studio-versioned/diagnosis-workbench/upstream-issues/`,
reviewed against `dataiku-diagnosis-toolkit` v0.38.13 (commit `5b39adb`) on 2026-10-25.

Each file answers one issue and is written to stand alone, so the workbench repo can copy the status, the fixed-in
version and the answers to the open questions into its own `UPSTREAM.md` and issue files.

| Issue | Verdict | Outcome | Fixed in |
|---|---|---|---|
| [UPS-001](UPS-001-response.md) Keynote rejects the standard deck | Valid bug | **Fixed** | plugin 0.38.14 (review generator 0.10.7) |
| [UPS-002](UPS-002-response.md) Standard deck uses Dataiku palette and font | Valid enhancement | **Implemented** as `v2.standard_theme` config | plugin 0.38.15 (review generator 0.10.8) |
| [UPS-003](UPS-003-response.md) Risk 2 slide section depends on hash seed | Valid bug | **Fixed** | plugin 0.38.16 (review generator 0.10.9) |
| [UPS-004](UPS-004-response.md) Appendix findings tables fixed to open statuses | Valid enhancement | **Implemented** as `v2.detail_statuses` config | plugin 0.38.17, default changed in 0.38.18 (review generator 0.10.10, 0.10.11) |

## What the workbench needs to do on adopting 0.38.15

1. Set UPS-001 to "fixed in 0.38.14" and re-run its opt-in integration test. `fix_presentation` is idempotent and does
   nothing once the deck declares its notes master, so it can stay as a safety net or be removed.
2. UPS-002: set `v2.standard_theme` (`dark`, `page`, `pale`, `font`) in the config it ships, then retire
   `apply_unbranded_theme`. Until then it keeps working, since the defaults are unchanged. Set UPS-002 to "fixed in
   0.38.15".
3. `validate_deck.validate()` now fails a deck that has a notes master but no `<p:notesMasterIdLst>`, or a
   `screen4x3` label on a non-4:3 page. A workbench pipeline that treats `structural_problems` as fatal will start
   catching this class itself.

## Where the fix is

The review generator is vendored here from `github.com/boonleeeu-dataiku/dataiku-review-generator`. The fix was made
there (0.10.7 and 0.10.8) and re-synced into `mcp-server-review-generator/`. 0.10.7 and 0.38.14 are pushed; 0.10.8 to 0.10.11 and 0.38.15 to 0.38.18 are committed locally, not pushed.
