# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project purpose

This repo (`dataiku-diagnosis-toolkit`) is a **deployable Claude Code plugin** that compiles
several related capabilities for reviewing Dataiku DSS diagnosis bundles. See `README.md` for
what each piece does. The plugin as a whole is versioned via `.claude-plugin/plugin.json`'s
top-level `version` field, bumped independently of the versions carried by the individual pieces
below.

The repo also carries `.claude-plugin/marketplace.json`, making it self-hostable as its own
single-plugin marketplace (`dataiku-local`) — see README's [Installation](README.md#installation)
section for the `/plugin marketplace add` / `/plugin install` flow this enables, both locally and
from GitHub.

## Plugin-level version bumps

Whenever the plugin's top-level version is bumped, update it in **all four** of these files
together — they must always carry the same value:

1. `.claude-plugin/plugin.json` — `version` (Claude plugin manifest)
2. `.claude-plugin/marketplace.json` — `plugins[0].version` (mirrors the plugin manifest)
3. `plugin.json` (repo root) — `version` (Codex's primary manifest)
4. `.codex-plugin/plugin.json` — `version` (Codex plugin manifest)

Also add a corresponding entry to the top-level `CHANGELOG.md`. This is independent of the
versions carried by the vendored components (see below) and by the two authored-here skills,
which have none.

## Vendored vs. authored-here components

- **`skills/dataiku-diagnosis-reader/`** is **vendored** from a
  separate upstream repo, `github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`, which is its
  actual source of truth. That repo versions it (SemVer in `SKILL.md`'s `version` frontmatter,
  with its own `CHANGELOG.md`) per its own `CLAUDE.md`. The upstream repo no longer has an MCP
  server; agents read the skill files directly and run `scripts/orient.sh` with Bash.

  To re-sync after upstream changes: diff the upstream repo's `dataiku-diagnosis-reader/`
  directory against this repo's `skills/dataiku-diagnosis-reader/` copy (content,
  `references/*.md`, `scripts/orient.sh`, version frontmatter, `CHANGELOG.md`), and port over
  whatever differs. Don't hand-edit content in this directory here expecting it to persist — fix
  it upstream and re-sync, or the next sync will silently overwrite the fix.

  **How to read a bundle is owned by the reader, never by the checklist skill.** When a checklist
  or calibration change needs a new "where does X live / how do I read it safely" fact (a file
  path, a JSON key, a log format, a column meaning), add it to the upstream reader's
  `references/*.md` (spot-checked against a real bundle, per upstream's `CLAUDE.md`), re-sync, then
  have the checklist skill point to that reference. Don't write the fact into
  `skills/dataiku-diagnosis-checklist-review/` — `calibrations.md` holds judgment (which status to
  give) only. `tests/test_skill_boundaries.py` enforces this; extend its `READER_OWNED_TERMS` when
  a new layout term shows up.

- **`skills/dataiku-diagnosis-checklist-review/`**, **`skills/dataiku-review-deck-builder/`** and
  **`skills/dataiku-diagnosis-log-review/`** are authored directly in this repo. None has an upstream, and none currently carries an
  independent `version`/`CHANGELOG.md` — don't add versioning to either speculatively; that
  decision is deferred until one needs to be shared/versioned on its own.

  `skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx` is a bundled
  default checklist the skill falls back to when the user has no checklist of their own — unlike
  the gitignored, user-supplied/sample assets under `mcp-server-review-generator/resources/`
  (see below), this one is **tracked in git**: it's not customer data, it's small, and it must
  ship with the plugin for the default to work for anyone installing it via the marketplace.

  `skills/dataiku-diagnosis-log-review/` is built to be extractable: it depends on the reader (`scripts/logscan.py`,
  `references/logs.md`) and on the generator's `write_log_workbook` tool only, never on the checklist or deck code.
  Its `references/error-catalogue.md` holds judgment (cause, confidence, mitigation); log formats, masking and
  how to read a log belong in the reader. When a new log signature turns up, add its layout to the reader upstream
  and its entry to the catalogue; `tests/test_log_review_contracts.py` checks the entries are complete.

- **`mcp-server-review-generator/`** is **vendored** from a separate upstream repo,
  `github.com/boonleeeu-dataiku/dataiku-review-generator`, which is its actual source of truth.
  That repo versions itself independently (SemVer in its own `VERSION` file, `CHANGELOG.md`, git
  tags) per its own `CLAUDE.md`.

  To re-sync after upstream changes: diff the upstream repo's `scripts/`, `config/`, `tests/`,
  `VERSION`, `CHANGELOG.md`, `requirements.txt`, `requirements-dev.txt`, and `pytest.ini` against
  this repo's `mcp-server-review-generator/` copy, and port over whatever differs. Don't hand-edit
  content here expecting it to persist — fix it upstream and re-sync, or the next sync will
  silently overwrite the fix.

  `resources/` is out of scope for this sync: the branding template is a manual, gitignored,
  user-supplied asset (see below), and the sample completed checklist
  (`dku_diagnosis_2026-07-22_checklist_review.xlsx`) is likewise gitignored here — it's a demo
  artifact for the checklist-to-deck pipeline, not referenced by any code, docs, or config, so
  there's nothing to keep in sync.

## Security / privacy

Never commit real Dataiku diagnosis bundle data (or copy any into this repo) — see the README's
"Security / privacy" section. `.gitignore` guards against the common shapes of this
(`dku_diagnosis_*/`, `diagnosis*.zip`) as defense-in-depth, but the rule is: this toolkit ships
code and docs only, never bundle data.

Separately, `mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx` (134MB) is
gitignored for a different reason — it's an internal brand asset over GitHub's 100MB file limit,
not customer data — and is never vendored in from upstream either; it's a manual, one-time,
user-supplied placement step (see README's "One-time setup").

`mcp-server-review-generator/resources/dku_diagnosis_2026-07-22_checklist_review.xlsx` is also
gitignored, for a third reason: it's a sample completed checklist with no customer data and no
runtime dependents (nothing passes it as a default `--checklist` path), so there's no reason to
carry it in the repo. It still exists locally for anyone who has it; it's just untracked.

## Working on the MCP server

Edits to `mcp-server-review-generator/scripts/**/*.py` take effect immediately (no build step),
but require the one-time `.venv` setup (see README) to exist before the server can launch at all
— the plugin ships Python source only, no committed virtualenv.

Whenever Claude makes edits to `mcp-server-review-generator/`,
remind the user afterward to also run Codex, so Codex can pick up the changes — Codex only
adapts to Claude-side changes post-hoc (see `AGENTS.md`) and won't see these updates otherwise.

Whenever Claude makes or discusses an update to `skills/dataiku-diagnosis-reader/`, remind the user to make the change in the upstream repo
(`github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`, sibling checkout, named `../Diagnosis Reader/` or `../dataiku-diagnosis-reader/` depending on the machine; `tests/test_vendored_drift.py` tries both, or set `DATAIKU_DIAGNOSIS_READER_REPO`)
and re-sync it here, so the next sync doesn't silently overwrite it. Likewise remind them to run
Codex afterward, since the skill copy is also read by Codex.

## Testing

See README's "Testing" section for the three tiers.
- **Before handing back any change**, run `scripts/test.sh fast`. It makes no model calls.
- After re-syncing from upstream, `tests/test_vendored_drift.py` confirms the copies match. It
  skips if the sibling upstream checkouts aren't on disk.
- **When the bundled checklist's checks change** (a renumbered, split, merged or removed check), run
  `scripts/test.sh fast`. `tests/test_calibration_ids.py` lists each stale entry in `calibrations.md` (checked
  against `tests/calibration_anchors.md`; the rules' own title anchors are checked against the checklist in `tests/test_rules_security.py`). Fix those entries and the anchors file together, then update `EVAL_ITEM_IDS` and
  `tests/fixtures/expected/*.yaml` if an eval item moved.
- **Where a status rule lives.** A check the facts can decide is a rule in `skills/dataiku-diagnosis-checklist-review/scripts/rules_*.py`,
  specified in `docs/verdict-rules.md` (one row per rule; `tests/test_verdict_rules_doc.py` fails when a rule and its row
  disagree on existence). `references/calibrations.md` holds only the model's `notes` guidance for those checks and the
  status logic of the model-decided ones. Change a rule, its row, its unit test in `tests/test_rules_*.py` and the fixtures together.
- **When you add or change a rule or a calibration**, extend the eval fixtures to cover it (see `tests/fixtures/README.md`):
  1. Add the item to `EVAL_ITEM_IDS` in `tests/fixtures/build_fixtures.py`.
  2. Shape a synthetic bundle so it triggers the calibration.
  3. Record the expected answer in `tests/fixtures/expected/*.yaml`.
  4. Regenerate the fixtures.
- **When you change a skill's wording that another component depends on** (status names,
  Summary block headers, the deck tool's return keys or error text), check
  `tests/test_contracts.py`.
- Strict `xfail` tests mark known gaps (record any in `CHANGELOG.md` → Unreleased → Known issues; none exist currently).
  When you fix one, remove its marker. Strict mode makes it fail as an unexpected pass until
  you do.
- Fixtures are synthetic only. The same rule as "Security / privacy" above applies: never derive
  them from a real bundle.
- `scripts/test.sh eval` and the scripts under `tests/evals/` cost real model usage. Run them only
  when the user asks, or after a skill or model change they want checked. Don't run them as
  routine verification.

