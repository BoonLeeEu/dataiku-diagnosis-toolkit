# Changelog

All notable changes to the `dataiku-diagnosis-toolkit` plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/). This tracks the plugin's own
top-level version (`.claude-plugin/plugin.json`), independent of the versions carried by
vendored components (`skills/dataiku-diagnosis-reader/`, `mcp-server-review-generator/`) — see
`CLAUDE.md`.

## [Unreleased]

## [0.38.17] - 2026-10-26

### Added

- Review generator 0.10.10: `v2.detail_statuses` in `config/deck_layout.yaml` chooses which statuses the appendix findings tables list (Fail, Partial, Needs Review, Pass; `[]` drops them). The default keeps today's decks. Requested as UPS-004 by the `diagnosis_workbench` adaptation.

## [0.38.16] - 2026-10-26

### Fixed

- Review generator 0.10.9: the rule-derived Risk 2 slide picks the same section on every run; ties for most failing checks go to the earliest section in checklist order (it used to depend on `PYTHONHASHSEED`). Reported as UPS-003 by the `diagnosis_workbench` adaptation.

## [0.38.15] - 2026-10-25

### Added

- Review generator 0.10.8: `v2.standard_theme` in `config/deck_layout.yaml` sets the standard (unbranded) deck's colours and font; defaults are unchanged. Requested as UPS-002 by the `diagnosis_workbench` adaptation.

## [0.38.14] - 2026-10-25

### Fixed

- Review generator 0.10.7: the standard (unbranded) deck opens in Keynote. It now declares its notes master and drops the stale 4:3 size label, and `validate_deck` reports both. Reported as UPS-001 by the `diagnosis_workbench` adaptation; see `upstream-responses/diagnosis-workbench/`.

## [0.38.13] - 2026-10-15

### Added

- Re-synced the diagnosis reader 0.22.0: new `groups` fact (SEC-008 counts) and `local_deployer` fact (ARCH-001 project and API deployer file counts).
- Review generator 0.10.6: `base_deck_path`, `--base-deck` and `DATAIKU_BRANDING_TEMPLATE` accept the folder holding the template.

### Changed

- `calibrations.md`: SCALE-001 Needs Review (embedded H2 inferred) guidance; SEC-008 and ARCH-001 use the new facts.
- `notes-format.md`: a Pass that must list items (SCALE-008 crash dumps) may run to 200 characters.
- README and CODEX_SETUP: renderer install hint; note that `*_verdicts.json` carries the instance id.

## [0.38.12] - 2026-10-14

### Added

- `run_step.py python` prints the interpreter to use for ad-hoc workbook scripts (this one if it has openpyxl, else the plugin virtualenv's), and the silent re-run under the virtualenv now says so on stderr.
- `scripts/preflight.sh` prints a trailing `renderer=soffice+pdftoppm|none` line. The deck-builder skill uses it to say whether a visual check was possible and how to install a renderer.

### Changed

- Re-synced the diagnosis reader 0.21.0: `backend_log` adds `top_error_patterns` and `run_as_user_missing`, new `crash_dumps` fact, `deployer` adds `remote_host_with_local_mode`. Re-synced review generator 0.10.5: `DATAIKU_BRANDING_TEMPLATE` environment variable, and the "Base deck not found" error names the setup step.
- Calibrations: SCALE-007 takes its pattern groups from `top_error_patterns`; SCALE-004 and SCALE-007 mention run-as-user-missing scenarios; SCALE-008 lists crash dumps in `notes` with an `Action:`. No status changes.
- Deck-builder skill: an unattended run must not search the disk for a branding template; it uses `allow_standard_deck`.
- Calibrations: SCALE-008's Pass note says crash dumps are not read by any check and asks for an `Action:` when the bundle holds some; ARCH-001 flags a local deployer with a remote host recorded, or trust-all-certificates on, as an `Action:` only.

## [0.38.11] - 2026-10-12

### Added

- `scripts/preflight.sh`: pure-bash host check that prints `TIER=FULL`, `SPREADSHEET` or `FACTS_ONLY` (with a `fix=` hint). The checklist-review, deck-builder and Codex workflow skills run it first and limit their output to the tier, so a host without Python 3.10+ gets the workbook at most and is told why instead of a missing deck tool.

## [0.38.10] - 2026-10-12

### Fixed

- Deck: large Risk 1 tile figures no longer wrap over their labels, and an owner card with many asks no longer overlaps its rows (re-synced review generator 0.10.4). Over-long tile figures, grouped ids and more than 14 asks per owner now fail with a message that says what to change.

### Changed

- `dataiku-review-deck-builder` length budgets list the tile figure and per-owner ask limits.

## [0.38.9] - 2026-10-11

### Changed

- `run_step.py verdicts` and `verify` re-run themselves under the plugin's own virtualenv Python (`DATAIKU_PYTHON`, the venv beside the plugin, `PLUGIN_DATA`, or Codex's plugin-data directory) when the default Python lacks openpyxl, and otherwise exit with one line saying how to fix it.
- SCALE-001's reason now says when only the external `internalDatabase.connection` override is absent (DSS then uses its embedded H2, an inference) instead of "settings missing from the bundle"; status unchanged.
- Re-synced the vendored review generator to 0.10.3: `write_summary` wraps and sizes long text and merges recommendation rows; the v2 risk slide says `One root cause` only when the narrative gives `linked_label`, else `Linked fixes`.

### Changed

- Re-synced the vendored review generator to 0.10.1 (Summary sheet read once, v1 no longer reads the checklist twice, dead code removed; deck output unchanged).
- Re-synced the vendored reader to 0.20.1: `SKILL.md` slimmed (164 to 113 lines, orient is now step 1) and `references/orient-fallback.md` added. No script changed.
- `verdict-rules.md` moved from `skills/dataiku-diagnosis-checklist-review/references/` to `docs/verdict-rules.md`: it is a maintainer spec the model never reads. `tests/test_skill_boundaries.py` still scans it for reader-owned layout terms.
- Checklist `SKILL.md` (230 to 202 lines): Verdicts is now its own step 2 (later steps renumbered; steps 4, 6 and 7 keep their numbers); removed repeated `notes` format, column lists, fact enumeration, reviewer format and status guidance; the evidence-planning step is one sentence; Deliver is a numbered list.

## [0.38.8] - 2026-10-11

### Changed

- README and `CODEX_SETUP.md` list the host requirements (Python 3.10+ with `venv`/`pip`, `bash`, PyPI access on first launch, a writable install location) and say that the plugin's own virtualenv supplies every Python dependency.

## [0.38.7] - 2026-10-11

### Changed

- Launcher: `DATAIKU_PYTHON` names a Python >=3.10 to use when none is on `PATH` (e.g. Codex's bundled runtime); `/opt/homebrew/bin` and `/usr/local/bin` are searched explicitly; failures are also written to `launcher.log` (in `PLUGIN_DATA` under Codex) since hosts hide stderr.
- ADVSEC reasons no longer read as if a disabled control were enabled: a miss now says `expected <control>, but <key>=false`.
- SCALE-010's Pass reason says storage formats are blank or the DSS default list (the rule already counted the default as blank).
- GENAI-010 and GENAI-011 now follow GENAI-009: Not Applicable when Agent Hub is not installed, Needs Review when it is.
- Re-synced the vendored review generator to 0.10.2 (curated section name for `Advanced Security Options (DSS)`).
- Bundled template's last tab renamed `Advanced Security Options (DSS)` (was the 31-character truncation with a trailing space, which some importers reject; old workbooks still match).
- `calibrations.md`: scope notes for SCALE-008, GENAI-001, ARCH-007 and ARCH-016 (what a Pass does not establish).

## [0.38.6] - 2026-10-11

### Fixed

- `run_step.py` crashed on Python <3.10 (`Path | None`); it now has `from __future__ import annotations`.
- `scripts/start-review-generator.sh` picks a Python >=3.10 (the `mcp` SDK needs it), rebuilds a venv built with an older one, and exits with a clear message when none is found, instead of the server silently not appearing (no `write_summary` tool).
- Checklist `SKILL.md` states the Python >=3.10 prerequisite and points to the manual Summary fallback first in step 6; README and `CODEX_SETUP.md` say Python 3.10+.

## [0.38.5] - 2026-10-08

Slimming pass on the skills and tests; no change to any verdict.

### Changed

- Checklist `SKILL.md`: the `notes` format moved to `references/notes-format.md`; verdict precedence is stated once; the reader pointers no longer restate the reader's rules.
- `calibrations.md`: 233 to 170 lines. The "Check anchors" table moved to `tests/calibration_anchors.md` (read by `tests/test_calibration_ids.py`); five "live check, write an Action" entries became one general rule.
- Deck builder `SKILL.md`: shorter base-deck fallback steps.
- `rules_*.py`: the shared `_missing` helper now lives in `verdicts.py`.
- `TODO.md`: trimmed to open items; vendored-repo follow-ups listed under "Upstream follow-ups".
- Tests: stale comments fixed, a duplicate assertion removed, the rule-coverage check in `test_rules_security.py` made strict.

## [0.38.4] - 2026-10-08

65 of 67 checks are decided by code; only ARCH-002 and ARCH-003 stay with the model. The 0.38.3 Codex runs (two, 2026-10-08) passed `verify` and matched all 65 ruled statuses.

### Changed

- **ARCH-009, ARCH-012**: Not Applicable when no Kubernetes cluster is attached, Needs Review when one is (was always Needs Review). They moved from `rules_review.py` to `rules_k8s.py`, with the notes guidance in the Kubernetes block of `calibrations.md`.
- `SKILL.md` (Verdicts): the model now quotes `deciding_values` in plain words, skips empty ones, and paraphrases the rule's reason, instead of pasting raw `deciding_values={}` text into `evidence_found`.

### Added

- `docs/validation-process.md`: maintainer guide to how a status is decided (the flow, who owns what, matching, conventions, how to change a rule, how it is tested), linked from `README.md` and `TODO.md`.

## [0.38.3] - 2026-10-08

65 of 67 checks are now decided by code (was 62). Only ARCH-002 and ARCH-003 stay with the model: they need a live web lookup (the current GA release, the supported-OS page).

### Added

- **GENAI-002** (`rules_k8s.py`): no Kubernetes cluster attached = Not Applicable; cluster attached = Needs Review (GPU nodes, compute capability and the local Hugging Face code environment can't be shown by a bundle). A missing Kubernetes fact or an unreadable attachment is Needs Review.
- **GENAI-011, SEC-003** (`rules_review.py`): always Needs Review. The model reports what the bundle shows (Agent Hub and group counts; the cgroup targets DSS controls and whether UIF is enabled, without naming files) and an `Action:` to confirm the rest.
- `verdict-rules.md` rows, `calibrations.md` notes guidance and anchors, unit tests, and fixtures (eval checklist now 49 items) for each.

### Changed

- `calibrations.md`: removed the model-decided entry for the feature-conditional GenAI checks (both are now ruled). `verdict-rules.md` "Stays with the model" now names only ARCH-002 and ARCH-003.

## [0.38.2] - 2026-10-08

Reader 0.20.0. 62 of 67 checks are now decided by code (was 46). The 0.38.1 Codex run (2026-10-08) matched all 46 ruled statuses.

### Changed

- **Policy**: ADVSEC-005 not restricted = Fail (was Needs Review). ADVSEC-006 a valid http or https custom URL, or the default logged-out page = Pass; a custom redirect with another scheme, or an unrecognised behaviour = Needs Review (was Fail / Not Applicable). ADVSEC-011 links not disabled = Needs Review (was Fail).
- `calibrations.md`: the model-decided entries for ARCH-001, ARCH-008/014/015 and SCALE-012 are now notes-only guidance; a new "Always Needs Review" block tells the model what to report for the seven always-Needs-Review checks.

### Added

- **Rules for 16 more checks.** ARCH-008/014/015 (no cluster = Not Applicable, cluster attached = Needs Review); ARCH-001 (Needs Review for every node type); `rules_review.py` with ARCH-009, ARCH-012, SEC-008, SEC-011, SCALE-005, SCALE-016, GENAI-010 (always Needs Review, the model reports observations and an `Action:`); SCALE-012 to 015 from the reader's new connection details (all set = Pass, some = Partial, none = Fail, no such connection = Not Applicable); GENAI-008 (always Needs Review, with a DSS 14.7 reason).
- `verdict-rules.md` rows for all of them and a new "Always Needs Review" section; unit tests and synthetic fixtures (eval checklist now 48 items) for each.

### Changed (vendored)

- `skills/dataiku-diagnosis-reader/` re-synced to 0.20.0: `facts.py` `connections` gains `cloud_storage` and `warehouses` (types and booleans only). The warehouse fast-write, Spark native and UDF settings are found by name pattern (a non-blank value counts as set); no Snowflake, Databricks, Redshift or Synapse sample exists to verify the names.

### Known issues

- SCALE-013 to 015 warehouse setting names are unverified against a real bundle.
- SCALE-012 is Not Applicable when no S3, Azure or GCS connection exists (the earlier note asked for Partial for HDFS-only storage).

## [0.38.1] - 2026-10-07

### Changed

- **`calibrations.md` restructured.** It is the file the model reads in full before every review, and 37 of its entries had become the specs of rules that code now decides, so it re-stated logic the model never applies (about 4,900 words). It now holds only what the model needs: the general principles, a compact "what to write" list (the `evidence_found`, `notes` and `Action:` guidance around each rule-decided status), and the status logic of the model-decided checks (ARCH-001, 002, 003, 008, 014, 015, SCALE-012, local Hugging Face, AI assistant debug data). About 2,400 words, the anchors table now listing only the ids it cites.
- **New `references/verdict-rules.md`**: the human-readable spec of all 46 rules as one table per rule module, with the conventions (missing fact = Needs Review, the known version-gate gap). The model does not read it during a review. SKILL.md, CLAUDE.md and the rule modules' docstrings point to it.
- Stale wording fixed: the rule-module reference (four modules, not one), ARCH-007's managed-versus-manual prose (the rule treats every cluster alike), ARCH-004's duplicated explanation, and the "Fail only on positive evidence" HTTPS line (the rule never Fails).

### Added

- `tests/test_verdict_rules_doc.py`: every registered rule has exactly one row in `verdict-rules.md`, and a row sits under its rule module's section. It caught a missing SEC-004 row while this was written.

## [0.38.0] - 2026-10-07

### Changed

- **SEC-010**: SSO enabled is Pass whatever LDAP is (the "SSO on, LDAP off = Needs Review" case is removed); SSO disabled stays Fail, a missing SSO flag Needs Review.
- **SEC-009**: LDAP enabled with no authorized groups is now Needs Review (was Fail); with groups it stays Pass, LDAP off Not Applicable.

### Added

- Deterministic verdicts, Batch 4a (partial), `scripts/rules_k8s.py`, from the new reader fact `kubernetes` (reader 0.19.0): **ARCH-005** (Spark off = Not Applicable; enabled with resource-setting configs = Pass, none = Fail; flag missing = Needs Review), **ARCH-006** (Spark off = Not Applicable; two or more differently sized configs = Pass, one or all identical = Needs Review, none = Fail), **ARCH-007** (per-user templated namespaces = Pass; a fixed or missing namespace = Needs Review), **ARCH-010** (a Kubernetes config with a memory limit = Pass, none defined = Fail), **ARCH-011** (two differently sized container configs = Pass, one or identical = Needs Review, none = Fail), **ARCH-013** (a Kubernetes cluster definition = Pass), **ARCH-016** (cluster attached: default cluster set = Pass, none set = Fail, no cluster attached = Not Applicable, anything else = Needs Review; the default execution config is a note only), **ARCH-017** (feature on with a default visual-recipe config = Pass, else Needs Review). With no cluster attached (no cluster file and no default cluster id) the Kubernetes-only checks are Not Applicable, even if Kubernetes execution configs are defined.
- ARCH-014 and ARCH-015 stay with the model (they need node-group and capacity data a bundle never holds).
- Eval fixtures cover ARCH-005, 007, 011, 016 and 017 (eval checklist now 41 items).

### Changed

- Reader re-synced to 0.19.0. `calibrations.md`: `[code-decided]` marks, the new Spark and Kubernetes case lists and anchors.

## [0.37.0] - 2026-10-07

### Added

- Deterministic verdicts, Batch 4c (partial), six more checks in `scripts/rules_platform.py`: **SCALE-002** (Hive metastore on a Hadoop estate or DSS-internal without one = Pass; Glue, an estate mismatch or an unknown flavor = Needs Review), **SCALE-003** (graphics export on = Pass, off or missing = Needs Review), **SCALE-004** (an active scheduled step-based scenario with cleanup steps in an admin project = Pass; scheduled but unclear purpose, or active but unscheduled = Needs Review; no candidate project or no active scenario = Fail), **SCALE-007** (any ERROR, FATAL or WARN in the backend logs = Needs Review, none = Pass), **SCALE-008** (Fail on any confirmed miss: below the RAM tier, under 3x the config folder, the 32-48 GB dead zone, or any OutOfMemoryError; Needs Review when nothing is missed but an input is absent; Pass when all met), **SCALE-010** (any non-blank connection, upload connection, engine or non-default storage-format preference = Needs Review, DSS's own default format list counts as blank).
- Reader 0.18.0 facts behind them: `metastore_and_exports`, `backend_log` (per-file level and OutOfMemoryError counts with time windows, counts only) and a `scripted` flag on admin cleanup scenarios.

### Changed

- Reader re-synced to 0.18.0. `calibrations.md`: `[code-decided]` marks and the new case lists for these six.
- Eval fixtures: the synthetic `backend.log` lines now use the real bracketed level format, and the baseline bundle carries a non-admin project so the SCALE-004 "no admin project" case is real rather than a missing directory.
- SCALE-012 to 015 (cloud storage, Snowflake, Databricks, warehouses) stay with the model: no connection facts yet.

## [0.36.0] - 2026-10-07

### Added

- Deterministic verdicts, Batch 4b (partial): `scripts/rules_genai.py` decides seven GenAI checks. From existing facts: **GENAI-003** (Trace Explorer default web app set = Pass, block present but unset = Fail, block missing = Needs Review), **GENAI-005** (Bring Your Own LLM inactive = Not Applicable, active with reference project and main LLM = Pass, either missing = Fail), **GENAI-006** (every LLM id ChatGPT 5.2 or later = Pass, any older = Fail, undeterminable = Needs Review), **GENAI-009** (Agent Hub installed = Needs Review, not installed or no plugin configuration = Not Applicable, never Pass or Fail). From the new reader fact `genai_settings` (reader 0.17.0): **GENAI-001** (default code envs internal = Pass, a non-internal one = Needs Review, none set = Fail), **GENAI-004** (terms accepted and AI Services enabled = Pass, otherwise Needs Review), **GENAI-007** (all three Cobuild default LLMs set = Pass, otherwise Needs Review). GENAI-002 and GENAI-011 stay with the model (no verified fact); GENAI-008 and GENAI-010 were never planned for code.
- Eval fixtures cover GENAI-003 and GENAI-004 (eval checklist now 36 items).

### Changed

- Reader re-synced to 0.17.0.
- `calibrations.md`: `[code-decided]` marks and entries for the seven rules, anchors for GENAI-003 and GENAI-004.

## [0.35.0] - 2026-10-07

### Added

- Deterministic verdicts, Batch 3b, from the new reader fact `server_config` (reader 0.16.0: whitelisted `install.ini` `[server]` and `config/dip.properties` settings, certificate locations reduced to yes/no): **SEC-006** (DSS terminates TLS itself, ssl on with a certificate = Pass; otherwise Needs Review, never Fail), **ADVSEC-007** (wiki upload extensions set = Pass, none = Fail), **ADVSEC-008** (any `dku.exports.disable*` key true = Pass, none = Fail), **ADVSEC-009** (the six core headers set with restrictive values = Pass, some header set but not all six = Partial, none = Fail; the other four headers are notes only), **ADVSEC-011** (`disableDataTableLinks` or `dku.feature.dataTableLinks.enabled=false` = Pass, neither = Fail). A missing `dip.properties` means nothing is set (Fail for ADVSEC-007 and 008). With 3a this completes Batch 3.
- `calibrations.md`: ADVSEC-007 entry, ADVSEC-009 now defines the six core headers and their restrictive values, SEC-006 notes that a proxy documented elsewhere stays Needs Review, `[code-decided]` marks, anchor for ADVSEC-007.

## [0.34.0] - 2026-10-07

### Added

- Deterministic verdicts, Batch 3a: `scripts/rules_security.py` decides the checks that read the instance's `security` settings block, from the new reader fact `security_settings` (reader 0.15.0, whitelisted keys only, the custom logout URL reduced to its scheme): **ADVSEC-001** (hide error stacks) and **ADVSEC-002** (hide version info): on = Pass, off = Fail; **ADVSEC-003** (both session timeouts 0 = Fail, either set = Pass); **ADVSEC-004** (one session per user: on = Pass, off = Fail); **ADVSEC-005**, **ADVSEC-012** and **SEC-007** (restricted visibility off, users may edit their name and email, secure cookies off): a deviation is Needs Review, because the checklist allows a deliberate choice; **ADVSEC-006** (no custom redirect = Not Applicable, valid http/https redirect = Pass, configured but invalid = Fail); **ADVSEC-010** (iframe hosting off = Pass, on with secure cookies off = Fail, on with secure cookies on = Needs Review). A missing setting or block is Needs Review.
- `calibrations.md`: new entry for the simple toggles, the `[code-decided]` marks, and anchors for the new ids.
- `tests/test_skill_boundaries.py`: rule modules may name the keys the reader publishes in `security_settings` (read from the reader's `SECURITY_KEYS`); every other reader-owned layout term is still rejected there.

## [0.33.2] - 2026-10-07

### Changed

- **ARCH-004** now decides from both evidence sources and no longer hands the row back to the model whenever the sanity check has messages. A sanity-check message whose code mentions rotational, HDD or SSD is Fail (even when the disks could not be read); otherwise any rotational disk is Fail, all disks non-rotational is Pass, and disks unknown is Needs Review. Found on the GE review: lsblk showed an SSD, the sanity check had 19 unrelated messages, and the rule needlessly returned `undecided`. `undecided` remains only for a facts output without message codes.
- Re-sync reader 0.14.0: `facts.py` `sanity_check` gains `codes` (distinct message codes, never the free-text details).

## [0.33.1] - 2026-10-07

### Changed

- **SCALE-001**: PostgreSQL on the same host (loopback) is now **Pass**, not Partial, with a `notes` comment that it is installed locally on the DSS host. Non-local PostgreSQL is still Pass and another database type is still Fail. The calibration entry, the rule, the unit test and the two fixtures' expected answers (baseline, admin-python) are updated together.

## [0.33.0] - 2026-10-07

### Added

- Deterministic verdicts, Batch 2: `scripts/rules_platform.py` decides **SEC-004** (cgroup memory cap against the checklist's RAM tiers: disabled = Fail, 80% of RAM or more = Needs Review, within 10% of the tier target = Pass, otherwise Needs Review), **SCALE-001** (PostgreSQL off-host = Pass, loopback = Partial, other type = Fail), **SCALE-006** (sanity-check output present = Pass, missing or empty = Fail), **SCALE-009** (any limit 0 or blank = Fail; none 0 but activities outside 30-50 or per-job not 5 = Needs Review; all in range = Pass), **SCALE-011** (`filesystem_root` present = Fail, absent = Pass) and **ARCH-004** (any rotational disk = Fail, all non-rotational with no sanity-check messages = Pass, disks unknown with no sanity-check output = Needs Review). A missing fact is Needs Review.
- A rule may now return "undecided" for a case the facts cannot settle; the row gets no verdict and appears under `undecided` in the `verdicts` output, and the model decides it. ARCH-004 uses it when the sanity check has messages, since its text may flag a rotational disk.
- `calibrations.md`: entries marked `[code-decided]`; new SCALE-011 entry and anchor; SCALE-009 and ARCH-004 entries record the cases above.

### Changed

- SCALE-008 (needs `OutOfMemoryError` counts from the backend logs) moves from Batch 2 to Batch 4c.

## [0.32.2] - 2026-10-07

### Fixed

- `run_step.py`: the facts hash in the run manifest no longer depends on where the bundle sits. `facts.py` prints the absolute bundle location (`bundle_root`, `mirror`), so `verify` failed with "a fresh facts.py run does not match the recorded hash" whenever the bundle was verified from another path than the run used (a staging copy, another machine). Those two fields are now left out of the hash. Manifests recorded before this still verify, from their original path.

## [0.32.1] - 2026-10-07

### Changed

- Found by reviewing the first Codex run on 0.32.0 (the five ruled items matched their verdicts, but the run left no manifest beside the workbook and wrote `Claude` as the reviewer):
- `validated_by` and the `write_summary` reviewer are now `<agent name> (AI-assisted review of <bundle name>)` in the shared checklist skill (`Claude`, `Codex`, ...), so no client needs an override. The Codex-only duplicate rule in `codex-skills/dataiku-codex-workflow/SKILL.md` is removed.
- Step 7 now says to copy `<stem>_run_manifest.json`, `<stem>_facts.json` and `<stem>_verdicts.json` into the same folder as the delivered workbook, so `verify` can be re-run on delivered output (agents that stage outputs in a work dir, such as Codex, previously left them behind).

## [0.32.0] - 2026-10-07

### Added

- Deterministic verdicts, Batch 1 (pilot): `scripts/rules_security.py` decides **SEC-001** (instance id: present = Pass, missing = Fail), **SEC-002** (UIF: disabled = Fail, enabled with a rule = Pass, enabled with no rules = Partial), **SEC-005** (no JEK-specific cgroup target = Pass, one or more = Fail), **SEC-009** (LDAP authorized groups) and **SEC-010** (SSO) from the saved facts; a missing fact is Needs Review. `verify` fails if the workbook disagrees. Their `calibrations.md` entries are marked `[code-decided]` and stay as the spec; tests check each rule against the fixtures' expected answers and the bundled checklist's titles.
- Re-sync reader 0.13.0: `facts.py` `cgroups` gains `target_counts` (targets per workload category). SEC-005 could not be decided before: a JEK target configured and no JEK category at all both read as an empty `workload_categories_with_no_placement`.

## [0.31.0] - 2026-10-07

### Added

- Deterministic verdicts, foundation (Batch 0; no rules yet, so reviews are unchanged): `scripts/verdicts.py` holds the rule registry
  (`@rule(id, anchor_title)`), the verdict shape (`id`, `status`, `reason`, `deciding_values`) and the five fixed statuses, and
  `run_step.py verdicts` computes verdicts from the saved facts and a checklist, saves `<stem>_verdicts.json` and records the step.
  Code is final: `run_step.py verify` now requires the verdicts step, hashes the saved `<stem>_facts.json` against the manifest, and fails
  naming any ruled row whose workbook status differs from its verdict. A rule applies only when the row's id and title both match
  (case, punctuation and spacing ignored); rows that match on one only are reported, never judged.
- SKILL.md: a "Verdicts" step (agent-neutral: run the command, copy each status exactly).

### Changed

- `run_step.py` robustness: a missing reader script, a corrupt manifest or an unreadable checklist now end in a one-line error or a
  `RUN VERIFY: FAIL`, never a traceback; a crashed or timed-out fresh `facts.py` run is reported as such.
- `tests/test_skill_boundaries.py` also scans the skill's scripts for reader-owned layout terms.

## [0.30.0] - 2026-10-07

### Added

- Re-sync reader 0.12.0: `facts.py` gains `sanity_check` (whether `run/sanity-check.json` is in the bundle and non-empty, plus message counts by severity).
- Calibration for **SCALE-006** (instance sanity check): output with messages = Pass, missing or empty = Fail, never Partial or Needs Review. The last round's only split item (Partial vs Pass over the same 15-19 warnings). Fixtures cover both outcomes; the admin-python fixture loses its sanity-check output, so its ARCH-004 becomes Needs Review.

## [0.29.1] - 2026-10-06

### Changed

- A plaintext internal-database password (from `facts.py`'s `internal_database`) is now reported the same way every run: SCALE-001 `notes` carry `Action: rotate the stored database credential and move it to a secrets store` (status unchanged), and the final summary carries one fixed line. The value is never printed. The baseline fixture stores a synthetic plaintext password and expects the Action.

## [0.29.0] - 2026-10-06

### Added

- Re-sync reader 0.11.0: `facts.py` gains `byo_llm` (Bring Your Own LLM active only when a main LLM id or reference project key is set; a custom LLM connection alone does not count).
- Calibrations for the four checks that still split repeat Codex runs: **ARCH-003** (supported OS: listed in Dataiku's docs for the DSS major = Pass, not listed = Fail, lookup failed or OS not captured = Needs Review), **SEC-005** (no JEK-specific cgroup target = Pass, a target configured = Fail, cgroup settings missing = Needs Review) and **GENAI-005 / GENAI-006** (BYO LLM inactive = Not Applicable; active: reference project + main LLM = Pass else Fail; model ChatGPT 5.2+ = Pass, 5.1 or earlier = Fail, unknown = Needs Review). Fixtures and expected answers cover them.

## [0.28.3] - 2026-10-06

### Added

- `skills/dataiku-diagnosis-checklist-review/scripts/run_step.py`: runs the reader's `orient.sh` and `facts.py` and records each in a `<stem>_run_manifest.json` (exit status, time, output hash; `facts` output saved as `<stem>_facts.json`), and a `verify` command that checks both steps ran, a fresh `facts.py` run matches the recorded hash, the Summary is present and current, and (with `--deck`) the narrative and deck exist. The skill runs both and reports the `RUN VERIFY` line. Tests in `tests/test_run_step.py`.

## [0.28.2] - 2026-10-06

### Changed

- Checklist-review skill pins the `write_summary` header formats (reviewer = the `validated_by` string, node = `<nodetype> / DSS <version>`, diagnosis date = `YYYY-MM-DD`) and how recommendations are grouped and ordered (one per root-cause group, at most 7, Fail first), so repeat runs produce the same Summary. Contract test added.

## [0.28.1] - 2026-10-06

### Added

- Calibration for **SEC-010** (SSO enablement): SSO disabled = Fail (whatever LDAP is), SSO and LDAP both enabled = Pass, SSO enabled with LDAP off or either setting missing = Needs Review. Uses the reader's existing `facts.py` `sso_and_ldap`; no reader change. Fixtures and expected answers cover all three outcomes.

## [0.28.0] - 2026-10-06

### Added

- Re-sync reader 0.10.0: `facts.py` now also reports `data_volume_device` (the disk behind the data directory and its ROTA value), `admin_cleanup_scenarios` (housekeeping-project scenarios: type, active, trigger state, step names; scripts never read), `deployer` (mode and target host, never the API key) and the LDAP authorized-groups count; plus reader guidance not to open the Deployer API key block raw (a repeat run printed it).
- Calibrations for the checks that still split repeat Codex runs: **SEC-001** (instance id present = Pass, missing = Fail), **SEC-009** (LDAP on with authorized groups = Pass, on with none = Fail, off = Not Applicable), **ARCH-004** (decide from the disk behind the data directory, since DSS's sanity check can be missing: all non-rotational = Pass, any rotational = Fail, undeterminable = Needs Review) and **SCALE-010** (any non-blank default connection/format/engine preference = Needs Review, all blank = Pass).

### Changed

- SCALE-008 calibration: size the config folder from `facts.py`'s `config_folder_size` (listing-based), never the partial mirror.
- Fixtures grow from 25 to 28 eval items (SEC-001, SEC-009, SCALE-010) and the `k8s_remote` bundle gains `lsblk` blocks so ARCH-004 is `[Pass]`; `tests/test_facts.py` covers the new facts, including that the deployer key and group names are never printed.

## [0.27.2] - 2026-10-06

### Changed

- Calibrations no longer depend on check ids staying the same. `calibrations.md` (and the checklist-review `SKILL.md`) now say to match an entry by what the check is about; the ids are pointers into the bundled checklist, and an entry is never applied just because an id matches. A new "Check anchors" table records the title each cited id had when its entry was written.
- `tests/test_calibration_ids.py` fails when an id cited in `calibrations.md` is missing from the table, or when the bundled checklist no longer has that id with that title (renumbered, renamed or removed), listing each stale entry. `CLAUDE.md` documents the maintenance step. No calibration outcome changes.

## [0.27.1] - 2026-10-06

### Changed

- SEC-004 (cgroup memory cap) calibration rewritten to judge the limit against the checklist's RAM tiers (over 120 GiB: 75% of RAM; 60-120 GiB: 66%; 30-60 GiB: RAM minus 20 GiB; under 30 GiB: 50%). Within 10% of the tier target is **Pass**, including slightly above it; 80% of RAM or more is **Needs Review** (over-allocation risk); more than 10% off the target, or no memory limit, is **Needs Review**. Previously a flat "roughly 50-75%" left a 75.7% cap to run-to-run judgment (Pass/Partial/Partial across three runs).
- Fixtures: `synthetic_design_k8s_remote` now has host RAM in `/proc/meminfo` form and a memory cgroup cap inside the Pass band, so SEC-004's expected answer is `[Pass]`; `tests/test_facts.py` covers the cgroup percentage.

## [0.27.0] - 2026-10-06

### Added

- Re-sync reader 0.9.0: `scripts/facts.py <bundle_root>` prints a deterministic, secret-safe JSON report of the settings reviews most often need (heap sizes, host memory, `config/` size from the listing, database host, concurrency limits by leaf-key search, SSO/LDAP, user isolation, cgroups, `filesystem_root`, Trace Explorer, default preferences, plugins/Agent Hub), with an explicit `ABSENT` for a missing setting. Added after repeat reviews of one bundle disagreed on 14 of 67 items, mostly because hand reads mis-stated or missed values.
- `tests/test_facts.py` (synthetic fixtures only).

### Changed

- Checklist-review `SKILL.md` runs `facts.py` after `orient.sh` and treats its values as the source of truth, citing each `source` in `evidence_found`. `tests/test_skill_boundaries.py` now requires that wiring.
- This is also the release that lets Codex load it: a Codex plugin install is cached per version, and the previous commits kept 0.26.4, so Codex runs never saw `facts.py`.

## [0.26.4] - 2026-10-06

### Changed

- Skill tidy-up, no change to any status outcome: linked-computer/device plumbing moved out of the checklist-review `SKILL.md` into `references/linked-computer.md` (shared with the deck builder, so the commit-and-verify rule lives once); `calibrations.md` regrouped by theme under general principles, keyed by checklist item id, with the duplicate HTTPS entries merged and the version-currency lookup procedure moved into its entry; Secrets section trimmed to the delta over the reader's; deck-builder narrative rules turned into bullets.

## [0.26.3] - 2026-10-06

### Changed

- Re-sync reader 0.8.0: how to find a housekeeping project and read its scenarios (`step_based` vs `custom_python`).
- SCALE-004 calibration rewritten: scenario scripts are never read; unconfirmed intent is Needs Review, not Partial. Fixtures use real step shapes and add a third bundle (`synthetic_design_admin_python`).

## [0.26.2] - 2026-10-06

### Changed

- Re-sync reader 0.7.0: documents where the metastore flavor (`metastoreCatalogsSettings.synchronizeTo.flavor`) and `graphicsExportsEnabled` live.
- Fixed the synthetic fixtures' metastore key to the real nested shape; graphics export with the setting absent is Needs Review.

## [0.26.1] - 2026-10-06

### Changed

- Re-sync reader 0.6.0: documents where user isolation (UIF) lives (`general-settings.json` → `impersonation`), which the SEC-002 calibration relies on.
- Fixed the synthetic fixture's impersonation rule key (`type`, as in real bundles, not `rule`).

## [0.26.0] - 2026-10-05

### Changed

- Checklist-review calibrations for the 11 items whose status differed across three repeat runs on the
  same bundle (SEC-002, SEC-004, SEC-006, ADVSEC-008, ADVSEC-009, SCALE-001/002/003/004, ARCH-006,
  GENAI-007). New general rule: judge only what the bundle shows; live-check aspects go in `notes` as an
  `Action:`, not in the status. Fixed statuses for UIF, cgroups memory limit, export restriction, security
  headers, external PostgreSQL, metastore, graphics export, admin-project cleanup and Spark baselines; HTTPS
  with DSS-terminated TLS is Pass; a version gate beats a feature gate (GENAI-007).
- Eval fixtures extended to 25 items covering each new calibration, in both synthetic bundles.

## [0.25.0] - 2026-10-05

### Changed

- Skill guidance from three repeat test runs (no generator or reader changes). Checklist-review and
  deck-builder: verify every `device_commit_files` by reading the device file back, and recommit under a new
  staged filename if stale (a repeat commit of the same `stagedPath` could report `written` but keep the old
  bytes); explicit paths, never a glob over the outputs parent. Deck-builder: per-field character budgets for
  the narrative, since neither the generator nor `validate_deck` catches slide text overflow. Checklist-review:
  document the bundled-template workflow, check `get_device_info` before requesting folder access, read
  `priority` from its column, and note the output/narrative naming convention.

## [0.24.0] - 2026-10-05

### Changed

- Checklist-review calibrations now give fixed statuses for the three items that flipped between repeat runs
  on the same bundle (SCALE-007, GENAI-001, GENAI-009): any backend-log ERROR/WARN is Needs Review (clean is
  Pass); internal LLM Mesh code envs are Pass (non-internal Needs Review, nothing set up Fail); Agent Hub
  installed is Needs Review (not installed is Not Applicable). Eval fixtures and expected answers extended to match.

## [0.23.0] - 2026-10-05

### Changed

- Re-synced the vendored reader skill to 0.5.0: `peek.py` gains `--keys` / `--max-items`, redacts only string
  values and masks `apiKey`; stricter secrets rules (don't `head`/`cat` user scripts, never print a
  sub-object, a secret's length or broad metadata); new verified reference facts (session/link settings under
  `security`, webapp API-ticket groups, Agent Hub signals, `sanity-check.json` has no last-run timestamp, dmesg
  boot-relative times); pipe `orient.sh` verbatim.
- Bundled checklist template regenerated from checklist generator 0.3.0: ADVSEC-003/004/011 now point at the
  `general-settings.json` keys instead of saying UI-only, ARCH-008 notes it is worded for Kubernetes, GENAI-003
  keeps its hand-fixed path (now a tracked correction upstream, so the template is no longer hand-edited).
- `calibrations.md`: session/link checks judged from the value, custom post-logout redirect (Not Applicable when
  unset), Spark validation without Kubernetes, version-gated checks, inferred limits, dominant benign log patterns.
- Eval fixtures cover ARCH-008, ADVSEC-003 and ADVSEC-006; `READER_OWNED_TERMS` extended.
- Codex companion files adapted to the template-fallback and `orient.sh` piping changes.

## [0.22.0] - 2026-10-05

### Added

- Missing branding template no longer ends a run with no deck. The deck-builder skill now asks the user for the
  template first; if none is available (or the run is unattended) it calls the generator with
  `allow_standard_deck=true` for a standard, unbranded v2 deck and says plainly that it is not branded.
  Never a stub base deck.

### Changed

- Re-synced the vendored review generator to 0.10.0 (adds `allow_standard_deck`, and the `base_deck_used` and
  `branded` result keys; the "Base deck not found" error now names both remedies).

## [0.21.2] - 2026-10-05

### Changed

- Re-synced the vendored reader skill to 0.4.1: when `orient.sh` can't run where the bundle is, pipe it there
  (`bash -s -- <root>`) before orienting by hand.

## [0.21.1] - 2026-10-05

### Changed

- Checklist-review skill: linked-computer guidance now covers retrying a failed folder-access request, the
  stage/edit/commit/call/re-stage loop, and redacting values (not key names) in staged configs.
- Deck-builder skill: concrete render-to-image recipe for the visual check.

## [0.21.0] - 2026-10-05

### Changed

- Re-synced the vendored review generator to 0.9.1: the default v2 deck now has speaker notes. Its Findings slides
  carry each item's full Statement, Evidence and Notes, so text the table clips is still available. v1 output is
  unchanged. `finding_note_lines()` moved to `deck_shared.py`.

## [0.20.0] - 2026-10-05

### Changed

- Re-synced the vendored review generator to 0.9.0: deck styles are a registry, and the v2 deck no longer builds
  the full v1 deck to get its cover and end card. Deck output is unchanged. `tests/test_contracts.py` and
  `tests/lib/check_review_output.py` follow the helpers that moved (`data_checks`, `deck_shared`). The generator's
  `requirements.txt` already listed `python-pptx`; an existing `.venv` needs `pip install -r
  mcp-server-review-generator/requirements.txt`.

## [0.19.0] - 2026-10-04

### Changed

- Re-synced `skills/dataiku-diagnosis-reader/` to upstream 0.4.0: new `scripts/peek.py` (secret-masking view of
  bundle JSON), a stricter "Handling secrets" section, and the correct `connections.json` shape
  (`{"connections": {<name>: ...}}`). Prompted by a Codex run that guessed the shape wrong and printed a
  plaintext internal-DB password.
- Checklist-review skill: points to `peek.py`, and tells the agent to report plaintext credentials found in the
  bundle (file and kind only, never the value) with a rotate recommendation.
- Deck-builder skill: the success message now says up front that the deck needs a visual check.

## [0.18.0] - 2026-10-04

### Changed

- Re-synced `mcp-server-review-generator/` to upstream 0.8.0: `analyze_checklist`'s `shape` lists the allowed
  `tone`/`state`/`effort` values, owner suggestions cover every default-template ID prefix and more team names,
  and `analyze_checklist` / the build result report resolved paths and modified times.
- Re-synced `skills/dataiku-diagnosis-reader/` to upstream 0.3.1 (what to do when `orient.sh` can't run).
- Checklist-review and deck-builder skills: explain that the review-generator tools run on the user's
  computer (device paths, commit files before calling, container copies go stale after `write_summary`),
  advise passing `output_path`, list the narrative enum values (`state`, `tone`, `effort`), name a team in
  `Action:` lines so owners can be suggested, point to the reader's by-hand orient fallback, and tell the agent to
  compare the reported modified times against what it wrote.
- Re-synced `mcp-server-review-generator/` to upstream 0.7.6: v2 decks no longer silently drop items with an
  unrecognised/blank status or overwrite duplicate IDs (counted as Needs Review / first kept, with warnings).
- Re-synced `mcp-server-review-generator/` to upstream 0.7.5 (shared leading-number stripper, `STACK_ORDER`
  rename, shared default constants; no deck-output change).
- Hygiene pass: removed stale reader-MCP-era wording from README / checklist-review skill description,
  regenerated the eval mock tool schema (now all 4 tools), removed the obsolete
  `docs/upstream-reader-spec.md`.
- Re-synced `mcp-server-review-generator/` to upstream 0.7.4 (dead-code removal, config parsed once,
  v2-specific manual QA checklist; see its CHANGELOG).
- Small trims: one-server loop in `scripts/refresh-eval-tool-schemas.sh`, redundant `.gitignore` line,
  hoisted a test import.

## [0.17.1] - 2026-10-04

### Changed

- Re-synced `skills/dataiku-diagnosis-reader/` to upstream 0.3.0 (secrets section, shorter description,
  trimmed quick lookup, `orient.sh` first when triaging).
- `dataiku-diagnosis-checklist-review`: Secrets section now points at the reader's "Handling secrets"
  instead of carrying its own rules.
- Codex companion: host-specific `validated_by` label and version-lookup adaptation.

## [0.17.0] - 2026-10-04

### Changed

- `dataiku-diagnosis-checklist-review`: defines "must-have" as `priority == must_have`; reads each row's
  `insufficient_evidence_handling` before deciding; fixed `validated_by` string; one notes budget (320
  chars, bullets <= 80); stop rule for unverified node types; final self-check; linked-computer steps
  gathered into one block; version-lookup procedure moved from `calibrations.md` into the skill;
  secrets guidance made self-contained.
- `calibrations.md`: judgment only. An attached cluster with no containerized config is now an explicit
  **Fail**; the config-variety rule is stated precisely; item ids are examples, not keys.
- `dataiku-review-deck-builder`: narrative key list replaced by a pointer to `analyze_checklist`'s `shape`;
  host-neutral tool loading; machine-specific path reference removed.
- `dataiku-codex-workflow`: dropped facts duplicated from the task skills.
- `docs/upstream-reader-spec.md` §6: reader skill hygiene changes to make upstream.

## [0.16.0] - 2026-10-04

### Removed

- `mcp-server-diagnosis-reader/` (and `scripts/start-reader.sh`, the `reader` Codex launcher, the
  `dataiku-diagnosis-reader` entries in `.mcp.json`/`mcp.json`/`.codex-plugin/plugin.json`, and the
  `reader-crash-triage` plugin eval). It only re-exposed the reader skill's docs as MCP resources
  and `orient.sh` as a `run_orient` tool; the skill and `scripts/orient.sh` (run with Bash) cover both.
  The plugin no longer needs Node.js/npm. Removed upstream too.

### Changed

- `dataiku-diagnosis-checklist-review`: orient step runs the reader's `scripts/orient.sh` instead of
  `run_orient`; the no-skills fallback reads the reader's `SKILL.md` and `references/` directly.
- Re-synced `skills/dataiku-diagnosis-reader/CHANGELOG.md` (dropped the MCP versioning note).

## [0.15.3] - 2026-10-04

### Fixed

- Re-synced `mcp-server-review-generator` to upstream v0.7.3: narrative `risk1`/`risk2`/`risk3` titles now get the
  "Risk N:" lead added when missing, so slides 4-6 are always labelled.

## [0.15.2] - 2026-10-04

### Changed

- `dataiku-diagnosis-checklist-review`: never print secrets (parse selected keys only, don't read stray notes
  files); never pick a checklist among similar templates; search `dip.properties` for advanced-security keys;
  bracketed `[ERROR]` log grep with time windows; full SCALE-008 rule (3x config folder, dead zone, jek/fek);
  `WebFetch` fallback for the version lookup; cleaner Not Applicable headline wording.
- `dataiku-review-deck-builder`: ask for the customer name instead of inferring it; narrative figures must be
  quoted from checklist cells, not self-tallied; `risk1`-`risk3` titles must carry their "Risk N: " prefix.

## [0.15.1] - 2026-10-04

### Fixed

- Re-synced `mcp-server-review-generator` to upstream v0.7.2: a `risk3` card whose `ids` is a string (allowed by
  the narrative shape) no longer fails the deck build with `KeyError: 'S'`.

## [0.15.0] - 2026-10-04

### Added

- Re-synced `mcp-server-review-generator` to upstream v0.7.1: a narrative with a wrong-typed field (a list where
  a string is expected, e.g. `risk2.positives`) is now rejected with every offending field named by path instead
  of a bare type error, and `analyze_checklist` returns a `shape` map of the expected types.

### Changed

- `dataiku-review-deck-builder`: the narrative key list now states field types, and says to fix the field named
  in a rejection rather than reading the generator's source.

- `dataiku-diagnosis-checklist-review`: the version-currency check now requires an extended web search plus a
  look for the next major; `diag.txt` (`lsblk` ROTA) is a named source for SSD checks; new calibrations make
  GenAI feature-conditional checks Not Applicable when the feature is unused, say to search for a hinted
  setting's leaf key before calling it absent, and treat `jekSettings.maxRunningJobs=0` as a Fail and
  HDFS connection-detail sanity findings as Partial.
- Default checklist template: GENAI-003 `parameter_hint` now points at
  `generativeAISettings > llmTraceSettings > traceExplorerDefaultWebApp`.

## [0.14.0] - 2026-10-03

### Added

- Re-synced `mcp-server-review-generator` to upstream v0.7.0: a new `write_summary` tool writes the checklist's
  Summary sheet deterministically (metadata, block headers and their one shared style, counts, per-section
  tallies and finding rows come from the section sheets), so its layout no longer varies with the model that
  wrote it. Critical Findings / Other Must-Have blocks are now read with all five columns, so a Summary status
  that disagrees with the section sheet is reported.

### Changed

- `dataiku-diagnosis-checklist-review` step 6 now has Claude call `write_summary` with a key point per must-have
  finding and the ordered recommendations, instead of hand-writing the sheet. The layout stays documented as the
  fallback if the tool is unavailable. `dataiku-review-deck-builder` notes the Summary must be written first.
- `tests/lib/check_review_output.py` also checks the Summary's block headers, counts and finding ids against the
  section sheets; `tests/test_contracts.py` pins the skill to `write_summary`'s parameters.

## [0.13.0] - 2026-10-02

### Added

- Re-synced `mcp-server-review-generator` to upstream v0.6.0: a new `analyze_checklist` tool returns the facts a
  v2 narrative must cite (checklist hash and narrative path, Needs Review and Not Applicable ids, quick-win
  candidates, validation rules), and a v2 build with no narrative now returns `narrative_missing` /
  `narrative_warning` (the CLI warns too).

### Changed

- `dataiku-review-deck-builder` now has Claude call `analyze_checklist` before drafting the narrative, and treat
  `narrative_missing` as a prompt to draft one and rebuild.

## [0.12.0] - 2026-10-02

### Changed

- `dataiku-review-deck-builder`: drafting the v2 `narrative.json` is now a required step whenever Claude runs
  the skill (finalize checklist, draft narrative from that bundle's rows, record `checklist_sha256`, then build;
  fix and rebuild if the tool rejects it; report whether `narrative_used`). Only a plain script run with no LLM
  may build without one. Previously this was guidance a run could skip, giving a generic fallback deck.
- `dataiku-diagnosis-checklist-review`: when the user also asks for a deck, it hands off to the deck builder
  and its narrative step instead of building without one.

### Added

- Contract tests that fail if either skill drops the narrative requirement.

## [0.11.0] - 2026-10-02

### Changed

- Re-synced `mcp-server-review-generator` to upstream v0.5.0: v2 is the default style, a v2 build
  auto-discovers `<checklist_stem>_narrative.json` beside the checklist, and warns when the checklist changed
  since the narrative was written. `*_narrative.json` is gitignored (it holds customer findings).
- The deck-builder skill now states that the reviewer who owns the checklist owns the narrative.

## [0.10.0] - 2026-10-02

### Added

- Verdict-first "v2" Platform Review deck: re-synced `mcp-server-review-generator` to upstream v0.4.0, adding
  `style="v2"` (now the default; `"v1"` keeps the old deck) and an optional `narrative_path` to `build_platform_review_deck`. The `dataiku-review-deck-builder`
  skill now asks for v2 and drafts the `narrative.json`, which the tool validates against item statuses.
- `python-pptx` is a new dependency of the review generator (v2 only); the launcher reinstalls on the next start.

### Changed

- The generator sync also picks up upstream v0.3.1 (Other Must-Have Items drops empty trailing columns).

## [0.9.0] - 2026-10-02

### Changed

- Updated the bundled `checklist_template.xlsx`: every item sheet gains a `statement_short` column
  (a one-sentence, slide-ready rewrite of `statement`).
- Re-synced `mcp-server-review-generator` to upstream v0.3.0: `statement_short` is now a required
  checklist column, and the deck's findings table and critical-finding cards show it (falling back to
  `statement` when empty). Speaker notes keep the full statement.

## [0.8.0] - 2026-10-02

### Changed

- `dataiku-diagnosis-checklist-review`: the `notes` column is now a crisp, slide-ready summary (a
  headline plus up to 3 `•` bullets, ~320 characters, no file paths), so a downstream deck can use
  it on its own. `evidence_found` stays the detailed audit trail (paths, keys, log lines). The
  Summary `Key point` column is held to one short line too.
- `tests/lib/check_review_output.py` lints `notes` for length, bullet count and file paths.
- Re-synced `mcp-server-review-generator` to upstream v0.2.0: the deck's findings table now shows
  `notes` only (falling back to `evidence_found` when empty), multi-line cells render as one
  paragraph per line, and speaker notes list Evidence and Notes separately.

## [0.7.0] - 2026-10-02

### Added

- A three-tier test setup. `scripts/test.sh fast` runs the deterministic tiers; `scripts/test.sh
  eval` runs the LLM evals. See README's Testing section.
  - Unit test suites for both vendored MCP servers (via re-sync to upstream
    `mcp-server-review-generator` v0.1.6 and `mcp-server-diagnosis-reader` v0.2.2):
    `mcp-server-review-generator/tests/` (pytest, including regression tests for the v0.1.4/v0.1.5
    fixes and a golden deck snapshot) and `mcp-server-diagnosis-reader/test/` (`node:test`).
  - Toolkit-level tests in `tests/`: cross-component contracts, manifest version and path
    consistency, vendored-copy drift against the upstream checkouts, and
    `tests/lib/check_review_output.py`, a checker for completed review workbooks.
  - Synthetic eval fixtures (`tests/fixtures/`): two hand-built bundles, a trimmed 11-item eval
    checklist, and expected answers that encode the checklist-review calibrations.
  - LLM evals: `claude plugin eval` cases in `evals/` (reader crash triage; deck builder's
    missing-template and `data_warnings` handling, with mocked tools), and
    `tests/evals/run_review_eval.py` + `compare.py` for scoring checklist-review runs per item
    and comparing them against a saved baseline.

### Changed

- `dataiku-diagnosis-checklist-review` step 6 now prescribes the exact Summary-sheet layout the
  deck generator parses. That covers header texts and order, a shared header style, metadata
  labels, table columns, and literal counts rather than `COUNTIF` formulas. Before this, the
  first live eval runs showed the model wording headers freely: one run titled the counts block
  "Overall status" and dropped the per-section header, which made the Summary unreadable by
  `build_platform_review_deck`. The skill's own earlier wording, "Per-section status
  breakdown", was also never recognized by the deck generator.
- The same step now says to leave an empty Critical Findings / Other Must-Have block with only
  its header rows. The baseline eval runs showed the model writing placeholder rows like "None -
  no must-have items failed.", which the deck generator would render as a finding with ID
  "None".

### Fixed

Via `mcp-server-diagnosis-reader` re-sync to upstream v0.2.2:

- The server's MCP `initialize` response reported a stale hardcoded version (`0.1.0`). It now
  reads the version from `package.json`. Re-run `npm run build` in `mcp-server-diagnosis-reader/`
  to pick this up.

### Known issues

Surfaced by the new tests and recorded as a strict `xfail` test rather than fixed:

- The review generator reads Critical Findings / Other Must-Have Summary blocks with only 3
  columns. In the skill's `ID | Section | Title | Status | Key point` layout, a Summary status
  that disagrees with the section sheet is never reported. The fix belongs upstream in
  `dataiku-review-generator`.

## [0.6.1] - 2026-09-30

### Fixed

Via `mcp-server-review-generator` re-sync to upstream v0.1.5:

- Findings & Risks chapter divider said "0 checklist items assessed" when the Summary sheet's
  Overall Status Counts block had no `Total` row; it now uses the section sheets' item count
  (matching the Executive Summary). A disagreeing `Total` row is reported in `data_warnings`.
- Critical Findings cards and the Executive Summary's Top-risk callout showed no section when the
  Critical Findings block had no `Section` column; section now falls back to the ID's section
  sheet display name.
- Critical Findings cards showed Excel-truncated section names (e.g.
  "Advanced Security Options (DSS"); they now always use the curated section display name.

## [0.6.0] - 2026-09-30

### Added

- `build_platform_review_deck` now returns `data_warnings` — Summary vs. section-sheet
  consistency checks (scorecard totals, missing sections, unknown or disagreeing IDs/statuses,
  uncurated section names) that structural validation can't catch (via
  `mcp-server-review-generator` re-sync to upstream v0.1.4).
- `dataiku-review-deck-builder`: surfaces `data_warnings` to the user and directs fixing the
  checklist and rebuilding, rather than hand-patching the generated deck.

### Fixed

Via `mcp-server-review-generator` re-sync to upstream v0.1.4:

- Results by Section scorecard showed all zeros for a section whose tab name has stray
  whitespace (e.g. the default template's `"Advanced Security Options (DSS "`).
- Critical Findings / Other Must-Have Items showed blank titles and mislabeled items as
  "Needs Review" when the Summary block lacked a `Title`/`Status` column; they now fall back to
  the section sheet's values.
- Long checklist IDs wrapping mid-code in narrow table ID columns.
- "Advanced Security Options" section now has a curated display name instead of the title-cased
  fallback "Advanced Security Options (Dss".

## [0.5.0] - 2026-09-30

### Added

- `dataiku-diagnosis-checklist-review`: new calibration for automation-node existence /
  Design–Automation separation checks (e.g. ARCH-001) on design-node bundles. Always marked
  **Needs Review**, since a design bundle cannot confirm a separate automation node. The review
  highlights a local deployer (`config/project-deployer/`, distinguishing populated from empty;
  `config/api-deployer/` noted separately as an API-node indication) or a remote deployer
  (`deployerClientSettings.mode = REMOTE`) as indications, and otherwise states that no
  definitive configuration exists and customer verification is needed. The deployer directories
  were also added to the skill's evidence-source list.

## [0.4.0] - 2026-09-28

### Added

- Bundled default checklist template for `dataiku-diagnosis-checklist-review`
  (`skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx`). If the user
  doesn't have their own checklist, the skill now offers to fall back to this bundled template
  instead of hard-requiring a user-supplied file.

## [0.3.0] - 2026-09-28

### Added

- Codex plugin support alongside Claude: repo-root `plugin.json` and `mcp.json` (Codex's own
  manifests), `.codex-plugin/plugin.json`, `codex-skills/dataiku-codex-workflow/SKILL.md`,
  `scripts/codex-start.sh`, `CODEX_SETUP.md`, and `AGENTS.md` repository guidance restricting
  Codex to its own files. Codex adapts to Claude-side changes post-hoc and never edits Claude's
  skills/MCP code.
