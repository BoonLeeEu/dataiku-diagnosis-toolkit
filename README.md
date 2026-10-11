# Dataiku Diagnosis Toolkit

A plugin for reviewing a Dataiku DSS diagnosis bundle: understanding its structure, safely
navigating it with the reader skill and `orient.sh`, and validating it against a checklist
spreadsheet.

## What's inside

- **`skills/dataiku-diagnosis-reader/`** — teaches the anatomy of a Dataiku DSS `diagnosis.zip`
  bundle: what files/directories exist, what format each is in, and where to find specific
  information. Includes `scripts/orient.sh`, which reports node type/version, the data-dir
  mirror location, and the largest/most relevant files in a bundle. Vendored from a separate
  upstream repo — see [Versioning & maintenance](#versioning--maintenance) below.
- **`skills/dataiku-diagnosis-checklist-review/`** — evaluates a diagnosis bundle against a
  checklist spreadsheet (columns like `id`, `priority`, `check_type`, `statement`,
  `expected_value`, etc.), filling in validation results and a summary tab. Falls back to a
  bundled default checklist template (`resources/checklist_template.xlsx` within this skill's
  own directory) if the user doesn't have their own checklist. Applies a set of user-defined
  check-specific calibrations (e.g. Kubernetes-conditional items, version currency, HTTPS behind
  a reverse proxy, automation-node existence from a design-node bundle) — see the skill's
  `references/calibrations.md`. Its `scripts/run_step.py` runs the reader's `orient` and `facts`
  scripts, computes rule-based status verdicts (`verdicts.py`), records every step in a run manifest, and `verify`s the finished review
  (including that statuses equal their verdicts). Authored
  directly in this repo.
- **`skills/dataiku-review-deck-builder/`** — step 2 of the workflow: turns a completed checklist
  (produced by `dataiku-diagnosis-checklist-review`) into a branded, customer-facing Platform
  Review `.pptx` deck, via the `mcp-server-review-generator` tools below. Authored directly in
  this repo. It builds the verdict-first "v2" deck (about 20 slides: verdict on Pass / applicable with
  N/A excluded, instance snapshot, three risks, quick wins, what we need from you, roadmap, then an
  appendix of Fail / Partial / Needs Review rows), with a `narrative.json` that the agent drafts
  from each bundle's own checklist on every run (the tool validates it against item statuses). A build
  without a narrative, possible only from the plain script, falls back to generic text derived from cells.
- **`codex-skills/dataiku-codex-workflow/`** — Codex-only companion skill that translates tool and
  file-access instructions for Codex (see [Codex plugin](#codex-plugin)).
- **`mcp-server-review-generator/`** — a local Python MCP server exposing
  `build_platform_review_deck`, `validate_deck`, `analyze_checklist` and `write_summary` tools that generate/validate the deck and
  return the facts its narrative must cite. Vendored
  from a separate upstream repo — see [Versioning & maintenance](#versioning--maintenance) below.

## Installation

> **Note:** full deck-generation functionality needs one manual step first — the Dataiku
> branding template can't be committed to git (134MB, over GitHub's 100MB limit). See
> [One-time setup](#one-time-setup) below.

This repo is both a plugin (`.claude-plugin/plugin.json`) and its own marketplace
(`.claude-plugin/marketplace.json`), so it can be installed directly without a separate
marketplace repo.

**From a local clone** (recommended while developing this repo itself — see caveat below):

```
/plugin marketplace add /path/to/this/repo
/plugin install dataiku-diagnosis-toolkit@dataiku-local
```

**From GitHub**, once changes are pushed:

```
/plugin marketplace add boonleeeu-dataiku/dataiku-diagnosis-toolkit
/plugin install dataiku-diagnosis-toolkit@dataiku-local
```

The Claude desktop app has the same flow under its Claude Code panel: **+** → **Plugins** →
**Marketplaces** tab → **Add marketplace** (same path/repo as above), then **Add plugin** to
install.

Caveat: a local-path install loads live from that directory (no separate cache copy), so the
`.venv/` from [One-time setup](#one-time-setup) below persists indefinitely and
`/plugin marketplace update` is a no-op. A GitHub-sourced install instead caches each commit
under `~/.claude/plugins/cache/...`; every time it's updated to a new commit, that's a **new**
cache directory with no prior build, so the lazy-bootstrap in `.mcp.json` reruns the full
build/install once. Expected and harmless, just not instant like the local case.

## One-time setup

The MCP server ships as source only — no committed
virtualenv — to keep the plugin small and avoid shipping a build that can drift from source.
`.mcp.json` doesn't invoke it directly; it runs `scripts/start-review-generator.sh`,
which lazily installs on first launch (comparing a stamp file against `requirements.txt` to skip
that step on later launches, and reinstalling automatically after a dependency change) and then
execs the real server. Install output goes to stderr, since MCP talks JSON-RPC over stdout.

Practically: the first time the server starts after installing or updating the plugin, expect
a delay of up to a minute or so while it installs; after that it starts instantly.

**Host requirements.** The launcher builds a private virtualenv and installs every Python
dependency into it (PyYAML, openpyxl, python-pptx, Pillow, lxml, `mcp`), so none of those need to
be installed on the host. The host needs only:

1. **Python 3.10 or newer, with the `venv` module and `pip`.** The `mcp` package requires 3.10+; Python 3.9 does not work.
   The launcher takes the first suitable interpreter from: `DATAIKU_PYTHON` (full path, if set), `python3.13` to
   `python3.10`, `/opt/homebrew/bin/python3`, `/usr/local/bin/python3`, then `python3` on `PATH`. If your 3.10+ is
   elsewhere (for example an app-bundled runtime), set `DATAIKU_PYTHON` to it.
2. **`bash`** on `PATH` (macOS/Linux native; Windows needs WSL or Git Bash, since `orient.sh` is also a shell script).
3. **Network access to PyPI on first launch**, for the `pip install` (and again after `requirements.txt` changes).
4. **A writable install location** for the virtualenv: the plugin folder under Claude Code, or the plugin-data
   directory under Codex.

If any of these is missing the server does not start and its tools (`write_summary`, `analyze_checklist`,
`build_platform_review_deck`, `validate_deck`) do not appear. The launcher writes its own failures (no suitable
Python) to `launcher.log`; `pip` errors appear only in the host's MCP server log. The review skill's manual
Summary fallback still works without the server, but the agent must then run the scripts with a Python that has
openpyxl and PyYAML.

If you'd rather not wait on the lazy build, you can still run the setup manually up front:

```sh
cd mcp-server-review-generator && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

**Required for deck generation:** the Dataiku branding template — an internal Dataiku brand asset, not committed
here (134MB, and not customer data — see "Security / privacy" below for why that's a different
concern from diagnosis-bundle data). Obtain it separately and place it at
`mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx`. Until that's done,
deck generation still works if you pass an explicit path to your own copy (the
`dataiku-review-deck-builder` skill will ask for one if the default path is missing). If you have no template at
all, the skill falls back to a standard, unbranded v2 deck (`allow_standard_deck`) and says so.

## Security / privacy

The review generator only reads the checklist, narrative and logo paths the calling agent gives it. **No diagnosis bundle data ships with this plugin** — never point it at, or copy
into it, real customer diagnosis bundles; treat any such bundle as private data to be supplied
by whoever is running a review, not part of the toolkit itself.

The Dataiku branding template used by `mcp-server-review-generator/` is a separate concern: it's
an internal Dataiku brand asset, not customer/bundle data, so it isn't covered by the warning
above — it's simply not committed here because of its size (134MB, over GitHub's 100MB limit),
the same reason its own upstream repo doesn't commit it either.

## How a status is decided

Code decides every check status the bundle's facts can settle; the model decides only the checks that need a web lookup and writes the
evidence and notes for all of them. `verify` fails a review whose workbook differs from the computed verdicts. The flow, the file
ownership and how to add or change a rule are in [`docs/validation-process.md`](docs/validation-process.md).

## Testing

Testing has three tiers, cheapest first. Run the first on every change. Run the third when
changing a skill, a calibration, or the model you use.

| Tier | What | Command | Cost |
|---|---|---|---|
| 1. Unit | The review generator's own suite, vendored from upstream: `mcp-server-review-generator/tests/` (pytest) | `scripts/test.sh fast` | none |
| 2. Toolkit | Cross-component contracts (template ↔ deck generator schema, skill ↔ tool wording), manifest consistency, vendored-copy drift against the sibling upstream checkouts, and the review-output checker | same command (`fast` runs tiers 1 and 2) | none |
| 3. LLM evals | The skills end to end with a real model, against synthetic bundles. `evals/` holds `claude plugin eval` cases for the deck builder, with mocked MCP tools. `tests/evals/run_review_eval.py` runs the checklist-review skill and scores its workbook item by item | `scripts/test.sh eval [--model <id>] [--runs 3]` | model usage |

**Tiers 1–2** need the one-time setup. `scripts/test.sh` adds `pytest` to the review generator's
`.venv` on first run. Two tests skip by design:
- The golden deck test skips without the branding template.
- The drift test skips without the sibling `../Dataiku Review Generator` and `../Diagnosis Reader`
  checkouts. Override their locations with `DATAIKU_REVIEW_GENERATOR_REPO` /
  `DATAIKU_DIAGNOSIS_READER_REPO`.

**Tier 3 and model changes.** The eval scenarios are synthetic bundles under `tests/fixtures/`.
Each is designed to trigger specific checklist-review calibrations, and its expected answers are
in `tests/fixtures/expected/*.yaml`. To check a model change or a skill edit:

```sh
mcp-server-review-generator/.venv/bin/python tests/evals/run_review_eval.py --model <current> --save-baseline
mcp-server-review-generator/.venv/bin/python tests/evals/run_review_eval.py --model <candidate>
mcp-server-review-generator/.venv/bin/python tests/evals/compare.py \
    evals/baselines/review-<current>.json evals/results/review/<stamp>/summary.json
```

`compare.py` flags any scenario or checklist item whose pass rate dropped by more than one run
in three. To check any finished review by hand, run
`tests/lib/check_review_output.py <review.xlsx> [--bundle <dir>]`. It confirms the workbook has
the schema and status vocabulary the deck generator needs, and that every evidence path it cites
exists in the bundle.

## Versioning & maintenance

This plugin's own release is versioned via `.claude-plugin/plugin.json`'s top-level `version`.

`skills/dataiku-diagnosis-reader/` is vendored from a separate
upstream repo (`dataiku-diagnosis-reader`), which is its actual source of truth and versions
it independently (see its `CHANGELOG.md` and `SKILL.md`'s `version` frontmatter). `mcp-server-review-generator/` is likewise vendored,
from `dataiku-review-generator`, versioned independently via its own `VERSION`/`CHANGELOG.md`.
`skills/dataiku-diagnosis-checklist-review/` and `skills/dataiku-review-deck-builder/` are
authored directly here and have no separate version. See `CLAUDE.md` for how to re-sync this
plugin with upstream changes.

## Codex plugin

This same repository also supports local installation in Codex. The Codex manifests (`plugin.json`,
`mcp.json`, and `.codex-plugin/plugin.json`) reuse the three task skills and the review-generator MCP server. The
additional `dataiku-codex-workflow` skill translates tool and file-access instructions for Codex.
Claude's plugin manifests and launch scripts remain separate.

Codex may already discover the `dataiku-local` marketplace from this repo's existing
`.claude-plugin/marketplace.json`. Check, then install the plugin:

```sh
codex plugin marketplace list
# If dataiku-local is absent:
codex plugin marketplace add /absolute/path/to/this/repo
codex plugin add dataiku-diagnosis-toolkit@dataiku-local
```

Start a new Codex session after installation. The Codex launcher prepares the local MCP server
in Codex's writable plugin-data directory on first use. It needs `bash` and Python 3.10+. Deck generation needs the branding template described in
[One-time setup](#one-time-setup). The template is gitignored, so a fresh GitHub install will not
include it. Put it in the installed Codex plugin's
`mcp-server-review-generator/resources/` directory for the default lookup, or keep it elsewhere
and pass its absolute path as `base_deck_path`. See [CODEX_SETUP.md](CODEX_SETUP.md#branding-template)
for the cache path and reinstall caveat.

See [CODEX_SETUP.md](CODEX_SETUP.md) for verification and update instructions.
