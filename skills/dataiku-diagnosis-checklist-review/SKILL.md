---
name: "dataiku-diagnosis-checklist-review"
description: "Evaluate a Dataiku DSS diagnosis bundle against a checklist spreadsheet using the dataiku-diagnosis-reader skill, filling in validation results and a summary tab. Falls back to a bundled default checklist template if the user doesn't have one. Use when the user asks to review/validate a Dataiku diagnosis against a checklist, or run a Dataiku instance health/compliance review."
---

# Dataiku diagnosis checklist review

Given (1) a Dataiku DSS diagnosis bundle directory and (2) a checklist spreadsheet of check items with empty result
columns (`validation_status`, `evidence_found`, `notes`, `validated_at`, `validated_by`), evaluate every row against the
bundle's actual contents and write the results back into the spreadsheet, plus add/update a Summary tab.

**Prerequisite:** the scripts need Python >=3.10 for the deck and MCP tools (`run_step.py` itself tolerates older ones). If `python3 --version` is older, run them with a newer
interpreter (e.g. `python3.12`, or the review generator's `.venv/bin/python3`). `run_step.py verdicts` and `verify` need
openpyxl and re-run themselves under the plugin's own virtualenv when the default Python lacks it; if it can't find one,
set `DATAIKU_PYTHON` to a Python 3.10+ that has openpyxl.

## Reference files (in this skill's `references/` directory)

- `notes-format.md` — the `notes` format and length budget. Read before writing the first `notes` (step 4).
- `calibrations.md` — **read in full before evaluating any row** (step 4). It holds the user's
  check-specific interpretations, which override a literal reading of the checklist: what to write around a
  rule-decided status, and the status logic of the checks no rule decides.
- `summary-layout.md` — manual Summary layout. Read only if `write_summary` is unavailable (step 6).
- `linked-computer.md` — device staging and commit-verify loop. Read only on a linked computer (step 0).

## 0. Inputs, access and tools

- **Host preflight (first).** Run `bash <plugin root>/scripts/preflight.sh` (from this skill's directory that is
  `../../scripts/preflight.sh`; it needs no Python) and read its `TIER=` line. Tell the user the tier and any
  `fix=` line in one sentence, then limit the output to it:
  - `FULL`: the workbook, Summary and, on request, the deck.
  - `SPREADSHEET`: the workbook (`run_step.py verdicts` / `verify` with the Python it names) and the manual
    Summary. No deck and no review-generator tools; say so rather than searching for them.
  - `FACTS_ONLY`: orient and facts findings in the chat only. No workbook, Summary or deck.
  If you cannot run the script, continue as `FULL` and fall back when a step fails for lack of Python.

- If the user hasn't given both paths, ask for the diagnosis bundle path and the checklist file
  path, nothing else up front. Start once you have both.
- Never pick a checklist yourself, even when the folder holds one obvious candidate or several
  similar templates (e.g. dated `*_checklist_template.xlsx` copies): a wrong guess silently changes
  the results. Ask, or offer the bundled default.
- If the user has no checklist handy, offer the bundled default template at
  `resources/checklist_template.xlsx` (relative to this skill's own directory), and say plainly once
  you proceed that you're using the default rather than a user-supplied checklist.
- **How to read the bundle comes from the reader, not from this skill.** Before touching the bundle,
  load the `dataiku-diagnosis-reader` skill (if skills can't be loaded, read its `SKILL.md`, `references/limitations.md` and
  `references/listings-and-manifests.md`). Use its `lookup-table` / `data-dir-config` references to find where a setting
  lives, and its large-file rules (grep/head/wc, never load whole). If the reader lacks a layout fact you need, say so in your
  final summary rather than recording it in this skill.
- Load the `xlsx` skill before reading/writing the spreadsheet.
- If the checklist has a version-currency or supported-OS check, confirm a web search tool is available; it is
  needed to look up the latest Dataiku DSS release (procedure in `references/calibrations.md`, DSS version currency).

### Files on a linked computer

If this session is linked to the user's computer (remote-devices tools present) and the paths are
local, read `references/linked-computer.md` before step 1. It covers folder access, staging, and the
commit-and-verify loop the generator tools need.

### Secrets

Follow the reader's "Handling secrets" section (open config JSON with its `scripts/peek.py`, never
dump whole files). Also:

- Never copy a secret into `evidence_found`, `notes`, the narrative or the deck. If one gets printed,
  say so in your final summary, name the file, and tell the user to rotate it.
- If the bundle itself holds plaintext credentials (e.g. an internal-database password), report that
  even if you never printed the value: name the file and the kind of credential, never the value, and
  recommend rotating it and moving it to a secrets store. Put it in your final summary every time, in
  exactly this form: `Plaintext credential: the internal database password is stored in plaintext in <the
  settings file named in facts.py's internal_database source>; value not read. Rotate it and use a secrets
  store.` The SCALE-001 `notes` carry the matching `Action:` (see `references/calibrations.md`).

## 1. Orient

Run the reader's `orient.sh` first, through this skill's `scripts/run_step.py run orient <bundle_root>
--manifest <stem>_run_manifest.json` (it passes the output through unchanged and records that the step ran;
`<stem>` is the review workbook's name without `.xlsx`; keep the manifest beside it). It reports node type/version, the
largest files, and which key troubleshooting files are present. This
tells you what evidence is realistically available before you plan reads.

If it shows a node type the reader hasn't verified (e.g. `deployer`) or no data-dir mirror, say what
the bundle cannot support and mark the rows that depend on it **Needs Review**, not Fail.

Then run `scripts/run_step.py run facts <bundle_root> --manifest <stem>_run_manifest.json` once (it runs the
reader's `facts.py` and saves the JSON beside the manifest as `<stem>_facts.json`). It prints the key
settings many checks depend on, each with its `source`, and an explicit `ABSENT` for a setting that isn't in the
bundle. How to use it is in step 4. If it can't run or errors, say so in your final summary and
use the reader's normal procedure.

## 2. Verdicts

Run `scripts/run_step.py verdicts <bundle_root> --manifest <stem>_run_manifest.json --checklist <checklist.xlsx>`
(it only reads the checklist; use the file you were given). It prints JSON and saves it as `<stem>_verdicts.json`.
`verdicts` lists, for each row whose status the facts decide by rule, its `id`, `status`, `reason` and `deciding_values`.

- Write each listed `status` as that row's `validation_status`, exactly. Code is final: `verify` fails naming any row whose
  workbook status differs. Make `evidence_found` and `notes` agree with it, paraphrasing the reason and quoting `deciding_values`
  in plain words ("cluster_attached is false"), never as a raw dump (skip them when empty). If you think a rule is wrong, say so
  in your final summary (never in the workbook).
- A row that is not listed has no rule: decide it as in step 4. The list may be empty. `undecided` names rows that have a rule
  but whose case the facts cannot settle; decide those as in step 4 too.
- `title_mismatch` and `probable_renumber` name rows whose id and title don't both match a rule (usually a changed
  checklist). They get no verdict: decide them as in step 4 and name them in your final summary.

## 3. Read the checklist fully

Dump every sheet's rows into a working file — don't try to hold 50+ rows of context in your head.
Keep at least `id`, `priority`, `check_type`, `statement`, `parameter_hint`, `operator`,
`expected_value`, `unit`, `expected_condition_notes`, `supporting_evidence`, `contradicting_evidence`,
`insufficient_evidence_handling` and `ambiguity_notes` when present. Note the exact result-column
headers and their column positions per sheet (they may differ sheet to sheet).

`priority` is `must_have` or `nice_to_have`. "Must-have" below means `priority == must_have`. Read
it from the `priority` column; never infer it from the wording of the statement (a row that sounds
mandatory can be `nice_to_have`, and `write_summary` rejects a `key_points` entry for one).

For the rows no rule decides, group them by the source they need and read each source once, finding it via the reader's
`lookup-table` and other references.

## 4. Evaluate every row

**Use the `facts.py` output as the source of truth** for every value it covers: take the value from it,
cite its `source` in `evidence_found`, and quote the raw value behind any Pass or Fail on a setting. Don't
re-derive such a value by hand, and never contradict it from memory. `ABSENT` is not yet a Fail: follow
the reader's "Finding a setting reliably" before calling a setting absent. For a check it doesn't cover,
read the bundle the normal way.

First read `references/calibrations.md` in full and apply it to every matching row. Match by what the
check is about, not by id alone: ids can change between checklists, so if a row's id matches an entry but
its title is about something else, don't apply the entry. Where a row's
`insufficient_evidence_handling` says what to do when the bundle lacks the evidence, follow it; a
matching calibration overrides it.

A row with a verdict takes that status; `calibrations.md` then only tells you what to add to `evidence_found` and `notes`.

For each checklist item, decide one of five statuses, used consistently across the workbook: **Pass**, **Fail**,
**Partial**, **Needs Review**, **Not Applicable**. When to use the last two is in `calibrations.md` (General principles).

For each item, write:
- `evidence_found`: the audit trail — concrete citations with exact file
  path(s) and the specific key/value or log line(s) that support the finding.
  This stays detailed; it is not shown on slides. Don't put recommendations
  here.
- `notes`: the slide-ready summary. The deck builder shows this text to the
  customer in a table cell, so it must be crisp, scannable and self-contained, in the
  format of `references/notes-format.md` (read it before the first row). It carries the verdict, the decisive values, and the
  recommendation or caveat, and cross-references causally linked findings by id.
- `validated_at` / `validated_by`: today's date (`YYYY-MM-DD`) and, verbatim,
  `<agent name> (AI-assisted review of <bundle name>)`, where `<agent name>` is the AI agent doing the review (e.g. `Claude`,
  `Codex`), unless the user supplied a reviewer name.

Look actively for causal chains across items (e.g., a resource limit set to
a disabling value, paired with crash dumps and recurring error-log entries,
all pointing to one root cause) — call these out explicitly and prioritize
them, rather than reporting each row in isolation.

## 5. Write results back with openpyxl

Match each row by its `id` column (not by row number) when writing results,
so the mapping is robust to row reordering. Verify every id in the sheet got
a result and every result was consumed (no silent mismatches) before saving.

Run ad-hoc workbook scripts with the interpreter `python3 <this skill>/scripts/run_step.py python` prints: the default `python3`
often lacks openpyxl, and that command names one that has it.

## 6. Add/update a Summary sheet

If the `write_summary` tool is not available, skip to the manual fallback at the end of this step
(`references/summary-layout.md`). Otherwise, once every item's `validation_status` is filled in, call the `write_summary` tool of the
`dataiku-review-generator` MCP server. It recreates the `Summary` sheet as the first tab, so
re-running is idempotent. It computes the metadata labels, counts, per-section tallies and finding
rows (ID, Section, Title, Status) from the section sheets and applies one fixed style. You supply
only the judgment text:

- `checklist_path`, `reviewer`, `bundle`, and optionally `node_version` and `diagnosis_generated`.
  Fix their format so repeat runs produce the same Summary header:
  - `reviewer`: exactly the `validated_by` string.
  - `node_version`: `<nodetype> / DSS <product_version>` from `facts.py`'s `node`, e.g. `design / DSS 14.2.1`.
  - `diagnosis_generated`: an ISO date `YYYY-MM-DD`, from the timestamp in the bundle folder name
    (`dku_diagnosis_<node>_<YYYY-MM-DD-HH-MM-SS>`).
- `key_points`: `{item id: one line, <= 90 characters}` for **every** must-have item (`priority == must_have`) that is Fail,
  Partial or Needs Review, and for no other item. Echo the headline of the item's `notes`. The key
  order sets the row order within each block. List Fail items most causally central first.
- `recommendations`: the ordered actions, linked issues together and root cause before its
  symptoms. One action per root-cause group, at most 7, each naming its item ids in brackets (e.g.
  `[SCALE-008]`). Order the groups by the Fail key points first (the first Fail's group first), then Partial,
  then Needs Review. Leave out the numbering; the tool adds `1. `, `2. `, ...

The tool fails without touching the file if a key point is missing, extra, too long or multi-line,
or if any item has a blank or unknown status. Fix the input and call it again. It also re-reads
the saved sheet as the deck generator will and compares it to what it meant to write.

If the tool is not available, read `references/summary-layout.md` and write the sheet by hand to
that layout. The deck generator reads this sheet, so its layout must not drift. Use the header
texts `Overall Status Counts`, `Per-Section Breakdown`,
`Critical Findings - Must-Have Items Failing`, `Other Must-Have Items: Partial / Needs Review` and
`Priority-Ordered Recommendations` **verbatim**, and the metadata labels `Bundle:`,
`Node / Version:`, `Diagnosis generated:`, `Report generated:`, `Reviewer:`.

## 7. Deliver

1. Run `scripts/run_step.py verify <bundle_root> --manifest <stem>_run_manifest.json --checklist <review.xlsx>` (add
   `--deck <deck.pptx>` when a deck was built) and put its one `RUN VERIFY` line in your final summary. It also fails when a
   row with a verdict has a different status in the workbook. On FAIL, fix the named problem (usually a skipped step, a stale
   Summary or a status that differs from its verdict) and run it again. If the bundle sits on a separate computer the scripts
   can't reach, say the run could not be verified.
2. Check: every id has one of the five statuses; each `notes` is within budget with no file paths or secrets; the Summary was
   written after the last edit.
3. Keep the run files with the deliverable: copy `<stem>_run_manifest.json`, `<stem>_facts.json` and `<stem>_verdicts.json`
   into the same folder as the delivered workbook (an agent working in a staging folder must copy them out), so `verify` can be
   re-run later.
4. Send the updated file to the conversation. If the source came from the user's linked computer, also write it back to the same
   path (`references/linked-computer.md`) and say so in one line. With the bundled default template there is no original path:
   name the output `<bundle-name>_checklist_review.xlsx` (or the user's name for it).
5. Summarise headline results (counts plus the 1-3 most important findings) rather than repeating the checklist.

If the user also asked for a deck (or a "report and powerpoint"), continue with the `dataiku-review-deck-builder` skill and
follow its order of work in full, including the narrative (`<checklist_stem>_narrative.json`). Do not build the deck without one; if you cannot, say so in your
final summary.
