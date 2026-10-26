# Dataiku Platform Review Deck Generator

A small Python tool that turns a completed Dataiku DSS platform-review checklist (`.xlsx`) into a branded,
customer-facing "Platform Review" PowerPoint deck (`.pptx`). It's a plain, rerunnable script — no AI/LLM
session is needed at runtime.

See [INTENT.md](INTENT.md) for the project's purpose, principles, and non-goals.

This is the second step of a two-step workflow:

1. **Review a customer's DSS diagnosis bundle against a standardized checklist** — filling in a `.xlsx`
   checklist with per-item pass/fail findings and a Summary sheet of counts, critical findings, and
   recommendations. That step happens outside this repo.
2. **This repo**: turn that completed checklist into a slide deck, via `scripts/build_deck.py`.

## Requirements

- Python 3.10+
- Third-party packages: `openpyxl`, `PyYAML`, `Pillow` (see `requirements.txt`); the optional MCP server
  additionally needs `mcp`, also in `requirements.txt`

`python-pptx` is needed for the default v2 deck. The legacy v1 path (`--style v1`) does **not** use
it — `.pptx` files are edited directly as raw zip/XML packages (see [How it works](#how-it-works) below).

### v2 deck (verdict first)

`python3 scripts/build_deck.py --checklist X.xlsx --customer "Acme" [--style v2] [--narrative narrative.json]`
builds a ~20-slide deck: verdict (Pass / applicable, N/A excluded), instance snapshot, three risks, quick wins,
what we need from you (Needs Review by owner), roadmap, then an appendix of Fail / Partial / Needs Review rows.
`narrative.json` is optional: it carries the human-judgment text, and is validated against the checklist (see
`scripts/narrative.py`). Without it, slides use text derived from checklist cells, and the build says so
(CLI warning; MCP `narrative_missing`).

## Setup

```bash
git clone <this-repo>
cd "Dataiku Review Generator"
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

`resources/Dataiku Branding Template 2026.pptx` (134MB, the default `--base-deck`) is **not** tracked in git —
it's over GitHub's 100MB per-file limit. Obtain it separately (internal Dataiku branding asset) and place it
at that exact path before running `build_deck.py` without an explicit `--base-deck`.

Without the template, the MCP tool can still build a **standard, unbranded** v2 deck: pass
`allow_standard_deck=true` (it is off by default, so an unbranded deck is never produced silently). The result then
reports `base_deck_used: "standard"` and `branded: false`. v1 has no such fallback.

The standard deck's colours and font are set by `v2.standard_theme` in `config/deck_layout.yaml` (`dark`, `page`,
`pale`, `font`; each optional, defaulting to the Dataiku green and Roboto). Status and accent colours are not themed.
The branded deck ignores it.

The per-section appendix findings tables list Fail, Partial and Needs Review items by default. `v2.detail_statuses` in
the same file chooses the statuses (any of `Fail`, `Partial`, `Needs Review`, `Pass`; rows stay in that severity
order). `[]` drops the tables, and the build then warns if Needs Review items are left without a row. Passed checks
keep their own slide either way. Applies to the branded and standard decks.

## Usage

```bash
python3 scripts/build_deck.py \
    --checklist path/to/completed_checklist.xlsx \
    --customer "Acme Corp" \
    [--logo path/to/acme_logo.png] \
    [--output output/Acme_Corp_Platform_Review.pptx] \
    [--rows-per-slide 4] \
    [--include-pass-items] \
    [--base-deck "resources/Dataiku Branding Template 2026.pptx"] \
    [-v]
```

Only `--checklist` and `--customer` are required — everything else has a sensible default (see
`config/deck_layout.yaml`).

| Flag | Description | Default |
|---|---|---|
| `--checklist` | Path to a completed checklist `.xlsx` (required) | — |
| `--customer` | Customer name, shown on the title slide (required) | — |
| `--logo` | Optional customer logo image, spliced into the title slide | none |
| `--output` | Output `.pptx` path | `output/<customer>_Platform_Review_<date>.pptx` |
| `--rows-per-slide` | Max table rows per findings slide | `config/deck_layout.yaml`'s `table_rows_per_slide` |
| `--include-pass-items` | Also list Pass/Not-Applicable items in findings tables (not just Fail/Partial/Needs Review) | `config/deck_layout.yaml`'s `include_pass_items` |
| `--base-deck` | Base branded `.pptx` to build from | `resources/Dataiku Branding Template 2026.pptx` (the MCP tool also honours the `DATAIKU_BRANDING_TEMPLATE` environment variable; either may name the folder holding the template instead of the file) |
| `-v`, `--verbose` | Debug-level logging | off |

Build finishes by structurally validating the generated deck automatically. You can also run that check on
its own against any already-generated deck:

```bash
python3 scripts/validate_deck.py output/some_deck.pptx
```

### Tests

```bash
python3 -m pip install -r requirements-dev.txt   # adds pytest
python3 -m pytest                                # from the repo root
```

The suite builds synthetic checklist workbooks on the fly (`tests/conftest.py`), so it never needs a real
checklist. `tests/test_golden_deck.py` builds a full deck and compares its slide text against
`tests/golden/deck_summary.json`. It skips when the branding template isn't present. After an intended
output change, rerun it with `--update-golden` and review the JSON diff. `tests/test_mcp_server.py` skips
when the `mcp` SDK isn't installed.

Automated tests don't check visual layout. Before shipping a layout change, still open a generated deck in
PowerPoint/Keynote and walk through the manual QA checklist printed at the end of `build_deck.py`'s output.

## MCP server

`scripts/mcp_server.py` exposes the same two operations as an MCP (Model Context Protocol) stdio server, so
any MCP-capable LLM client (Claude Desktop, Claude Code, other MCP tools) can call them as tools instead of
running the CLI by hand. It's a thin wrapper — no deck-generation logic lives here — and only supports local
stdio (the client launches it as a subprocess on the same machine; there's no HTTP/remote mode).

Add to your MCP client's config (e.g. Claude Desktop's `claude_desktop_config.json`, or Claude Code's MCP
config), using an absolute path (and your venv's `python3` if you use one):

```json
{
  "mcpServers": {
    "dataiku-review-generator": {
      "command": "/absolute/path/to/.venv/bin/python3",
      "args": ["/absolute/path/to/Dataiku Review Generator/scripts/mcp_server.py"]
    }
  }
}
```

It exposes three tools:

- **`build_platform_review_deck`** — same parameters as the CLI flags above (`checklist_path`, `customer`
  required; `logo_path`, `output_path`, `rows_per_slide`, `include_pass_items`, `base_deck_path`, `allow_standard_deck` optional,
  same defaults). Returns `{output_path, structural_problems, data_warnings, manual_qa_checklist}` — it runs
  `validate_deck` automatically and includes the manual QA checklist when structural validation passes.
  `data_warnings` lists checklist inconsistencies the deck would otherwise silently absorb (section totals
  not matching Overall Status Counts, Summary IDs/statuses disagreeing with the section sheets, unknown
  status labels, uncurated section names) — fix the checklist and rebuild rather than patching the deck.
  Relative paths resolve against the repo root, not the server process's working directory.
  For `style=v2` it also returns `narrative_used` (path or null) and `narrative_missing` (true when no narrative was
  used, with a `narrative_warning`): the deck then carries generic text derived from cells, so an LLM-driven run
  should draft the narrative and rebuild.
- **`write_summary`** — takes `checklist_path`, `reviewer`, `bundle`, `key_points` ({id: one line <= 90 chars} for every
  must-have Fail/Partial/Needs Review item) and `recommendations`, and rewrites the Summary sheet (first tab) in the
  layout the reader expects: counts, per-section tallies and finding rows are computed from the section sheets.
  Bad input fails before the file is touched; the saved sheet is re-read and compared before it replaces the original.
  Run it once statuses are final and before `analyze_checklist`.
- **`analyze_checklist`** — takes `checklist_path`, returns the facts a v2 narrative must cite so a draft validates
  first time: `checklist_sha256` and `narrative_path`, counts, per-section counts, ids by status, root-cause groups,
  quick-win candidates, Needs Review items with a suggested owner, Not Applicable items, open (Fail/Partial)
  items, and the validation rules. Read-only.
- **`validate_deck`** — takes `pptx_path`, returns `{pptx_path, passed, problems}`.

To exercise the server manually before wiring it into a client, use the MCP Inspector (needs the `cli` extra,
not required at runtime): `pip install "mcp[cli]"` then `mcp dev scripts/mcp_server.py`.

## Checklist workbook format

The input `.xlsx` needs:

- A **Summary** sheet with bundle metadata and five narrative blocks, in order: Overall Status Counts,
  Per-Section Breakdown, Critical Findings, Other Must-Have Items, Priority-Ordered Recommendations. Blocks
  are located generically (by header style, not fixed row numbers), so row counts can vary freely between
  checklists. The Recommendations block accepts either a pre-numbered single-column list or a
  `# | Action | Related IDs` table.
- One sheet per review section, each row a checklist item with a fixed 27-column header (`id`, `priority`,
  `title`, `statement`, `statement_short`, `validation_status`, etc.) — this header must match by name; a sheet that doesn't
  conform fails fast with a clear error naming the missing/misnamed column.

See `CLAUDE.md`'s "Checklist workbook schema" section for the full column list, and "How much checklist
variation this actually tolerates" for the current limits of that flexibility (e.g. `validation_status` is
currently fixed to `Pass`/`Fail`/`Partial`/`Needs Review`/`Not Applicable`).

`resources/` includes sample checklists — both a blank template and a couple of completed reviews — useful
as a starting point or for testing changes.

## How it works

`build_deck.py` starts from a copy of a branding master `.pptx` (`resources/Dataiku Branding Template
2026.pptx` by default) and edits/clones specific slides in place to splice in the checklist's content —
Executive Summary KPI tiles, a Results-by-Section scorecard, Critical Findings and Recommendations
card-lists, and per-section Findings slides — then deletes every other unused slide from the master. All
`.pptx` editing is done as scoped string/regex substitutions on raw OOXML part text (never a full
parse-and-reserialize), since round-tripping through a generic XML parser or `python-pptx` risks corrupting
the branded template's formatting.

For the full architecture (module-by-module breakdown, the base-deck's slide layout, config knobs, and design
rationale), see `CLAUDE.md`.

## Versioning

This project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`). The current
version lives in the repo-root `VERSION` file (read at import time as `common.VERSION`), and
`CHANGELOG.md` tracks what changed at each release ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
format). Every generated deck's title slide includes a "Generated by Dataiku Review Generator vX.Y.Z"
line, and `--version` works on both `build_deck.py` and `validate_deck.py`:

```bash
python3 scripts/build_deck.py --version
python3 scripts/validate_deck.py --version
```

To cut a new release (manual — no automation, appropriate for this project's scale):

1. Move `CHANGELOG.md`'s `[Unreleased]` bullets under a new `## [X.Y.Z] - YYYY-MM-DD` heading; leave a
   fresh empty `[Unreleased]` above it.
2. Edit `VERSION` to `X.Y.Z`.
3. Commit both together (e.g. `Bump version to X.Y.Z`).
4. Tag it: `git tag -a vX.Y.Z -m "vX.Y.Z"`.
5. `git push && git push --tags`.

## Project structure

```
scripts/
  build_deck.py       # CLI entry point + the v1 deck builder
  build_deck_v2.py    # the v2 (verdict-first) deck builder
  styles.py           # registry of deck styles (CLI/MCP dispatch through it)
  deck_shared.py      # cover/end-card code shared by styles
  data_checks.py      # checklist consistency checks shared by styles
  deck_analysis.py    # v2's pure analysis rules
  narrative.py        # v2's optional narrative.json validation
  read_checklist.py   # checklist .xlsx -> structured data
  section_names.py    # section display-name lookup
  validate_deck.py    # structural validation of a generated deck
  common.py           # shared paths/config loading
  mcp_server.py       # MCP stdio server wrapping build_deck/validate_deck as tools
  office/             # low-level .pptx package/XML editing (no checklist knowledge)
config/
  deck_layout.yaml    # deck-generation tunables (rows per slide, thresholds, etc.)
  section_names.yaml  # curated section display names
tests/                # pytest suite (synthetic checklists, golden deck snapshot)
pytest.ini            # pytest config (testpaths, default options)
requirements-dev.txt  # dev dependencies (pytest)
resources/            # branding master deck + sample checklist workbooks
output/               # generated decks land here by default
VERSION               # this tool's own SemVer version (read as common.VERSION)
CHANGELOG.md          # what changed at each version
```
