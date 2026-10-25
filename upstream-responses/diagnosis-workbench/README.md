# Responses to `diagnosis_workbench` upstream issues

Replies to the issue write-ups in
`github.com/boonleeeu-dataiku/diagnosis_workbench` → `code_studio-versioned/diagnosis-workbench/upstream-issues/`,
reviewed against `dataiku-diagnosis-toolkit` v0.38.13 (commit `5b39adb`) on 2026-10-25.

Each file answers one issue and is written to stand alone, so the workbench repo can copy the status, the fixed-in
version and the answers to the open questions into its own `UPSTREAM.md` and issue files.

| Issue | Verdict | Outcome | Fixed in |
|---|---|---|---|
| [UPS-001](UPS-001-response.md) Keynote rejects the standard deck | Valid bug | **Fixed** | plugin 0.38.14 (review generator 0.10.7) |
| [UPS-002](UPS-002-response.md) Standard deck uses Dataiku palette and font | Valid observation, deliberate behaviour | **Not changed**, pending a design decision | not scheduled |

## What the workbench needs to do on adopting 0.38.14

1. Set UPS-001 to "fixed in 0.38.14" and re-run its opt-in integration test. `fix_presentation` is idempotent and does
   nothing once the deck declares its notes master, so it can stay as a safety net or be removed.
2. Leave `apply_unbranded_theme` (UPS-002) in place. Nothing it depends on changed: `06312E`, `FEFEF9`, `D6E4E2`
   and `Roboto` are still the values in the standard deck.
3. `validate_deck.validate()` now fails a deck that has a notes master but no `<p:notesMasterIdLst>`, or a
   `screen4x3` label on a non-4:3 page. A workbench pipeline that treats `structural_problems` as fatal will start
   catching this class itself.

## Where the fix is

The review generator is vendored here from `github.com/boonleeeu-dataiku/dataiku-review-generator`. The fix was made
there (0.10.7) and re-synced into `mcp-server-review-generator/`. It is not yet committed or pushed in either repo.
