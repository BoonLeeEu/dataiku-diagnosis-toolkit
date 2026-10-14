---
name: "dataiku-review-deck-builder"
description: "Turn a completed Dataiku DSS platform-review checklist spreadsheet into a branded, customer-facing Platform Review PowerPoint deck. Use when the user has a reviewed/validated checklist (e.g. produced by the dataiku-diagnosis-checklist-review skill) and wants a slide deck to share with the customer."
---

# Dataiku review deck builder

This is step 2 of the two-step workflow: `dataiku-diagnosis-checklist-review` evaluates a
diagnosis bundle against a checklist and writes validation results into the workbook; this skill
turns that completed workbook into a `.pptx` deck. If the user hasn't reviewed the checklist yet,
suggest running that skill first — this one expects a checklist that already has
`validation_status`/`evidence_found`/`notes` filled in.

## 0. Tools

First run `bash ../../scripts/preflight.sh` (from this skill's directory; no Python needed). If its `TIER=` is not
`FULL`, stop: tell the user the deck needs Python 3.10+ on the host, give them its `fix=` line, and offer the
checklist workbook as the deliverable. Do not search for the generator tools or retry.

`write_summary`, `analyze_checklist`, `build_platform_review_deck` and `validate_deck` come from the
bundled `dataiku-review-generator` MCP server. If they are deferred, load them with your host's tool
discovery (in Claude Code, `ToolSearch` with `select:<name>,...`). Names may carry a server prefix.

## 1. Generate the deck

**Order of work (required whenever you, an LLM, are running this skill):**
1. Make sure the checklist is final, including its Summary sheet (the review skill writes it with
   `write_summary`; if it is missing or stale, call that first). Any later edit changes its hash.
2. Call `analyze_checklist` on the checklist, then draft the narrative (next section) from its output
   and this checklist's rows, for this bundle only. It returns `checklist_sha256`, the `narrative_path`
   to save to, the Needs Review and Not Applicable ids your owner and N/A groups must each cover once,
   quick-win candidates, and the validation rules. Do not skip this step or build first and "add it
   later": the tool's fallback text is generic and is not customer-ready. Only a plain script run with
   no LLM present may build without a narrative.
3. Write `<checklist_stem>_narrative.json` beside the checklist (with the `checklist_sha256` from
   `analyze_checklist`), then build ("Build the deck" below).
4. If the tool rejects the narrative, fix the narrative and rebuild; never drop it to get a build through.
5. In your report, state whether a narrative was used (`narrative_used`). If the result has
   `narrative_missing: true` (with a `narrative_warning`), draft one and rebuild. If you can't, say so
   plainly and say the deck's judgment text is auto-derived and needs reviewer rewriting.

**Container vs. device:** these tools run on the user's computer and read device paths only. If you
wrote the checklist or narrative in your container, follow `../dataiku-diagnosis-checklist-review/references/linked-computer.md`
(commit, then verify on the device, before calling a tool). Pass an `output_path` in the user's own
outputs folder.

### Draft the narrative (v2)

**Ownership:** the reviewer who owns the checklist owns the narrative. You draft it, the reviewer reads and
edits it before the deck goes to the customer, and it is redrafted whenever the checklist changes. The tool
validates facts only (IDs, statuses, figures), not prose. It holds customer findings, so never commit it.
Save it beside the checklist as `<checklist_stem>_narrative.json`; the tool finds it without `narrative_path`.
Add `"checklist_sha256"` (from `shasum -a 256 <checklist>`) so a later build warns if the checklist changed.

The tool derives counts, root-cause groups, quick wins, the Needs Review split by owner and the N/A groups
from the checklist. The judgment text is yours: write it from this checklist's rows only, and never copy
another customer's text. All keys are optional; omitted ones fall back to text derived from the cells.
`analyze_checklist` returns the `shape` map with the exact keys and types; follow it rather than this file. Enumerated values: `snapshot[].state` is `ok`, `watch` or `neutral` (a dot
colour, not good/warn/risk); `takeaways[].tone` is `good`, `risk` or `win`; `effort` is `S`, `M` or
`L`. `suggested_owner` in the scaffold is only a hint: assign owners yourself. `owners` must cover every Needs Review item once and `na_groups` every N/A item once.
Text fields are single strings, never lists. A rejection names each wrong field by path: fix exactly those
fields instead of reading the generator's source.

Rules:
- Write plain `risk1`/`risk2`/`risk3` conclusion titles; the generator adds the "Risk 1: " lead if missing.
- Group findings by root cause (shared evidence, "see SEC-004" in Action text). Titles state a conclusion.
- Every figure on a main slide must appear in a checklist cell. Quote figures verbatim from the cells and
  never state counts you tallied yourself (e.g. "nine options fail"); the validator rejects them, so
  rephrase without the number or use one the cells carry.
- Never cite a Pass item as a problem unless it is under `caveats`. Effort is indicative.

**Length budgets.** `validate_deck` checks structure, never layout, and the generator does not shrink or
clip narrative text, so text that is too long overlaps its neighbour on the slide. Treat these budgets,
derived from the slide's text-box sizes, as ceilings (characters, spaces included):

| Field | Budget |
|---|---|
| `takeaways[].heading` | 26, one line |
| `takeaways[].body` | 150 |
| `highlights` | 170 |
| `risk1.risk` | 130 |
| `risk1.fix[].text` | 35, one line; at most 5 steps |
| `risk1.tiles[].number` | 8 characters; the figure shrinks to fit (use a short one, not a six-digit log total) |
| `risk1.tiles[].label` | 30; `note` 60 (the id is prepended) |
| `roadmap.*[].action` | 55; at most 4 items per column (5 only if every action fits one line, about 30) |
| `owners.groups[].asks` | one checklist id per ask (never `A-1 / A-2`); at most 14 per owner, and from 6 up each shows on one line |
| `owners.groups[].asks[].ask` | 40 when the owner has up to 5 asks, else 20 (one line); owner `notes` 100 |

Put the detail in the checklist's `notes` and `evidence_found`, which the deck's appendix carries, not in
these cards. If a render still shows overlap, shorten the narrative string rather than editing the deck.

### Build the deck

Call `build_platform_review_deck` with:
- `checklist_path` (required) — the completed checklist `.xlsx`.
- `customer` (required) — customer name, shown on the title slide. Take it from the user; if not
  given, ask. Never infer it from an old deck or file name in the same folder.
- `logo_path` (optional) — a customer logo image for the title slide.
- `output_path` (optional, but pass a device path in the user's outputs folder) — defaults to `output/<Customer_Slug>_Platform_Review_<date>.pptx`.
- `style` — `"v2"` (the default: verdict-first, about 20 slides). Pass `"v1"` (one findings slide per few
  items) only if the user asks for the long form.
- `narrative_path` (v2 only, optional) — a `narrative.json` you drafted above.
- `rows_per_slide` / `include_pass_items` (optional, v1 only) — layout tuning; leave unset unless the user
  asks for something specific.
- `base_deck_path` (optional) — only needed if the branding template isn't at its default location
  (see "If the base deck isn't found" below).
- `allow_standard_deck` (optional, v2 only, default false) — builds a standard, unbranded deck when the template
  is missing. Pass it only as step 3 of "If the base deck isn't found"; never on a first call.

This runs structural validation internally (no separate `validate_deck` call needed) and returns
`{output_path, structural_problems, data_warnings, manual_qa_checklist, base_deck_used, branded, generator_version, checklist_path, checklist_modified, narrative_modified}` (`narrative_modified` is v2-only; v2 adds
`slide_count, narrative_used, narrative_missing, narrative_warning (only when missing), applicable_count, pass_count, quick_wins, owner_groups`).

## 2. If the base deck isn't found

The tool needs `Dataiku Branding Template 2026.pptx` (134MB, not bundled with this plugin — see
this plugin's README). If the call fails with a "Base deck not found" error, work down this list and stop at
the first step that gets a deck:
1. **Ask for the template** (one short question). If the user has it, retry with `base_deck_path`; the README's one-time setup is
   the durable fix.
2. **Don't guess a path or build on a stub or blank presentation:** the generator edits the template's own slides. Don't search the
   disk for a copy either: a file with the right name may not be the approved template.
3. **Standard deck.** If the user has no template, says to go without it, or you cannot ask (an unattended run), call again with
   `allow_standard_deck=true` (v2; omit `base_deck_path`). Style v1 has no fallback: use v2 (tell the user) or report that the
   template is needed.

When you hand over a standard deck (`branded` is false / `base_deck_used` is `"standard"`), say so plainly: it is
not Dataiku-branded, and a branded one needs the template plus a rebuild from the same checklist and narrative.

## 3. Report results

- If `data_warnings` is non-empty, the deck built but may show wrong or missing values (e.g.
  section totals that don't match Overall Status Counts, or Summary rows whose ID/status disagree
  with the section sheets). List the warnings, fix the **checklist** (not the generated deck), and
  rebuild. A warning that a recommendation cites a Pass or N/A item means the checklist's own
  recommendations need fixing. Hand-editing the deck would leave the checklist wrong and get overwritten by the next
  build.
- If `structural_problems` is non-empty, don't declare success — list the problems and say the
  deck needs another look before sending it out.
- If empty, tell the user the deck was generated (give the `output_path`) and that it still needs a
  visual check before sharing, then relay
  `manual_qa_checklist` verbatim as follow-up steps — automated validation only checks structure
  (malformed XML, dangling relationships, leftover placeholder text), never visual layout, so this
  checklist is the only QA pass that catches that. If a renderer is available (e.g. LibreOffice:
  `soffice --headless --convert-to pdf <deck>`, then `pdftoppm -png` and look at the images), render
  the deck and check the slides yourself. Preflight's `renderer=` line says whether `soffice` and `pdftoppm` are installed; when it
  is `none`, say no renderer was available and that text overflow and layout were not checked (on macOS,
  `brew install --cask libreoffice` and `brew install poppler` add one).
- Any other tool error (missing checklist, bad logo path, schema mismatch in the checklist) comes
  through as a real, specific message — relay it as-is rather than paraphrasing.
