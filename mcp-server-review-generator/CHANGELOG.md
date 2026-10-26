# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.10.9] - 2026-10-26

### Fixed

- The rule-derived Risk 2 slide (no `risk2` in the narrative) picks the same section on every run. When sections tie for most failing checks, the earliest in checklist order wins; before, the choice depended on `PYTHONHASHSEED`. Reported as UPS-003 by the `diagnosis_workbench` adaptation.

## [0.10.8] - 2026-10-25

### Added

- `v2.standard_theme` in `config/deck_layout.yaml`: the standard (unbranded) deck's dark, page and pale colours and its font are configurable. Omitted keys keep today's values (Dataiku green, Roboto), so existing output is unchanged. Hex values are validated, and unknown keys are rejected. Status, chart and accent colours are not themed, and the branded deck ignores the block.

## [0.10.7] - 2026-10-25

### Fixed

- The standard (unbranded) v2 deck opens in Keynote. python-pptx writes the notes master part but not its `<p:notesMasterIdLst>` entry, so the deck now declares it before saving. The 16:9 page no longer carries python-pptx's stale `type="screen4x3"` size label.

### Added

- `validate_deck.validate()` reports a notes master that `presentation.xml` does not declare, and a `screen4x3` size label on a page that is not 4:3. These pass python-pptx, so they were invisible to the earlier structural checks.

## [0.10.6] - 2026-10-15

### Changed

- `base_deck_path`, `--base-deck` and `DATAIKU_BRANDING_TEMPLATE` accept a directory: it resolves to the branding template in it, or to the only `.pptx` there. No match, or several, is an error that lists what was found.

## [0.10.5] - 2026-10-14

### Added

- `DATAIKU_BRANDING_TEMPLATE`: optional environment variable holding the absolute path of the branding template. `build_platform_review_deck` uses it when `base_deck_path` is not given, so the template can live outside the plugin cache.

### Changed

- The "Base deck not found" error now also names the one-time setup step (the default location or the environment variable).

## [0.10.4] - 2026-10-12

### Fixed

- v2 Risk 1 tiles: the figure is sized to its box (24pt down to 14pt) instead of wrapping over the label. `risk1.tiles[].number` is capped at 8 characters, with an error that says so.
- v2 owners slide: a card with many asks switches to one line per ask, so rows no longer overlap. An owner may hold at most 14 asks; more is rejected with a message to redistribute.

### Changed

- A grouped owner or cited id (`ARCH-001 / ARCH-002`) is rejected with "give one checklist id per entry" instead of "not in any checklist section sheet". The scaffold rules now state the one-id and size limits.

### Known issues

- `validate_deck` is still structural only; it does not detect text overflow.

## [0.10.3] - 2026-10-11

### Changed

- `write_summary`: finding rows wrap (Section, Title, Key point) with a row height sized to the wrapped text, and each recommendation is merged across A:E, wrapped and sized, so long text is no longer clipped or spilling. The round-trip check still re-reads the sheet as the deck reader does.
- v2 risk slide: the root-cause card heading is `One root cause` only when the narrative gives `linked_label`; otherwise it reads `Linked fixes`.

## [0.10.2] - 2026-10-11

### Changed

- `config/section_names.yaml`: curated entry for `Advanced Security Options (DSS)` (closing paren, no trailing space), so the checklist template's last tab can drop the truncated, space-terminated name some spreadsheet importers reject. The old key stays for existing workbooks.

## [0.10.1] - 2026-10-08

Clean-up and efficiency pass; deck output is unchanged (golden decks identical).

### Changed

- `read_checklist`: the Summary sheet is read once into memory instead of re-streaming a read-only worksheet on every cell access (the parse was O(rows^2)).
- v1 builds no longer read the checklist a second time for data warnings: `build_deck.build_deck()` takes an optional `warnings_out` list and `styles._build_v1` uses it.
- The `include_pass_items` fallback is now `true`, matching `config/deck_layout.yaml` and the tool docs (it only applies if the config key is missing).
- `narrative.py` copies its shape with `copy.deepcopy`.
- `requirements.txt` declares `lxml` (imported directly) and its comments are corrected.

### Removed

- Unused code: `narrative.check_rows`, `office.text.placeholder_text_box`, `PIC_RE`, `SP_RE`, `remove_relationship_by_rid`, `office.slides.duplicate_slide`, `office.tables.extract_cells`, and the unread `cell_char_limits.description` config key.

### Fixed

- Stale docstrings and comments: the `mcp_server.py` header (four tools, not two entry points), the `read_checklist.py` column count (27), the `build_deck_v2.py` pipeline description, moved-function references in `build_deck.py` and `deck_analysis.py`, and the status colours in the v1 manual QA text.

## [0.10.0] - 2026-10-05

### Added

- `allow_standard_deck` on `build_platform_review_deck` (v2 only, default false). With the branding template
  missing it builds a standard, unbranded deck (plain python-pptx cover and closing slide, the v2 palette and
  slides, cover note "Standard layout (Dataiku branding template not applied)") instead of failing. A wrong
  explicit `base_deck_path` is still an error. The result carries `base_deck_used` (`template`/`standard`) and
  `branded`, and the manual QA text says the deck is not branded.
- `tests/test_standard_deck.py`.

### Changed

- The "Base deck not found" error now names both remedies (`base_deck_path`, `allow_standard_deck`); style v1
  says it has no unbranded fallback.

## [0.9.1] - 2026-10-05

### Fixed

- The default v2 deck had no speaker notes. Its Findings slides now carry each item's full Statement, Evidence and
  Notes in the notes pane, so text the table clips is still available. v1 output is unchanged.

### Changed

- `finding_note_lines()` moved from `build_deck.py` to `deck_shared.py` so every style can use it.
- `tests/test_speaker_notes.py` runs over the style registry and fails for any style without full-text notes.

## [0.9.0] - 2026-10-05

### Changed

- Deck styles are now a registry (`scripts/styles.py`). The CLI `--style` choices, the MCP `style` check and the
  manual-QA lookup read it, so adding a v3 is one module plus one entry. No deck output changes: the v1 golden
  and the v2 cover/end pin pass unchanged.
- The v2 deck no longer runs the whole v1 build and throws most of it away. Its cover and end card come from
  `deck_shared.build_cover_and_end_deck()`, and `build_deck_v2` no longer imports `build_deck`. The v1-only
  config keys therefore no longer affect v2 runs.
- `check_data_consistency`, `collect_data_warnings`, `build_scorecard_rows` and `items_by_id` moved from
  `build_deck.py` to `data_checks.py`; `default_output_path` moved to `common.py`; the cover code moved to
  `deck_shared.py`.
- Golden snapshots are per style: `tests/golden/deck_summary.json` is now `deck_summary_v1.json`, plus a new
  `deck_summary_v2.json`.

### Added

- Tests: `test_v2_cover_end.py` (pins v2's cover and end slides, including rels and notes) and `test_styles.py`.

### Fixed

- Docs: the checklist schema is 27 columns (`statement_short` follows `statement`), not 26.

## [0.8.0] - 2026-10-04

### Added

- `analyze_checklist` returns the resolved `checklist_path` and its `checklist_modified` time, plus
  `narrative_exists` and `narrative_modified` for the file at `narrative_path`; the build result returns
  `checklist_path`, `checklist_modified` and (v2) `narrative_modified`. A caller whose files live elsewhere (a
  sandbox agent with the tools on the user's computer) can now see when the copy this server read is stale.

### Changed

- Needs Review owner suggestions: `owner_by_id_prefix` now covers every prefix of the default checklist template
  (ARCH, SEC, SCALE as well as GENAI, ADVSEC), and `owner_keywords` recognise more team names (network, DBA,
  SRE, IAM, DSS admin, ...), so fewer items fall back to "Other".
- `analyze_checklist`'s `shape` now spells out the allowed values of `takeaways[].tone`, `snapshot[].state` and
  `roadmap.*[].effort`, and `rules` states the 8-card snapshot limit, so a draft no longer learns them from a
  rejected build.

## [0.7.7] - 2026-10-04

### Fixed

- The v2 build result's `quick_wins` and `owner_groups` came from the automatic analysis even when a narrative
  supplied its own, so they could disagree with the slides. They now report what the deck rendered.
- The Risk 1 "One root cause" card now lists the linked check IDs under its label.

## [0.7.6] - 2026-10-04

### Fixed

- A v2 deck silently dropped any item whose `validation_status` was unrecognised or blank (and a blank one got
  no warning at all), so "X of N applicable" was computed from a shrunken N. Such items are now counted as
  Needs Review (what v1 already showed) and the data warnings name them; blank statuses are now warned about too.
- A duplicate item ID silently overwrote the earlier row in v2's analysis. The first occurrence is now kept and
  a warning names the ID (v1 shows every row and warns the same way).

### Changed

- One shared `read_checklist.STATUSES` / `canonical_status()` replaces the three status lists and lookups in
  `build_deck`, `deck_analysis` and `write_summary` (which still raises on an unrecognised status).
- `check_data_consistency` takes `style` ("v1"/"v2") so its warnings describe what that deck does with the item.

## [0.7.5] - 2026-10-04

### Changed

- No deck-output change. The leading-number stripper existed three times with two regexes; it is now one
  `common.strip_leading_number` (the tolerant form, so v1 also strips "1 . Fix"). `build_deck`, `build_deck_v2`
  and `write_summary` use it.
- `deck_analysis.STATUS_ORDER` (the 4-status stacked-bar order) is renamed `STACK_ORDER` so it no longer shares
  a name with `build_deck.STATUS_ORDER` (the 5-status checklist order). Documented why v2's Needs Review is blue.
- The base-deck path and rows-per-slide fallbacks are `common.DEFAULT_BASE_DECK` / `DEFAULT_ROWS_PER_SLIDE`
  instead of literals repeated in `build_deck.py`, `build_deck_v2.py` and `mcp_server.py`.

## [0.7.4] - 2026-10-04

### Changed

- Hygiene pass, no deck-output change. Removed unused code (`common.SAMPLE_DECK`, `EXPECTED_SLIDES_MIN`,
  `figure_in`, `package.write_part`/`read_part`, `tables.expected_column_count`, `text.replace_within_shape`/
  `remove_picture`, an unused import and locals). `common.load_config` now parses each YAML once per process
  (callers still get their own copy). `read_checklist` closes its workbook. The two owner-grouping `assert`s
  are now `RuntimeError`s so they survive `python -O`.
- `manual_qa_checklist` is now style-aware: v2 decks (the default) get a v2 checklist instead of the v1 one
  (TOC / KPI tiles / scorecard) that didn't apply. `validate_deck.MANUAL_QA_CHECKLIST` is kept as the v2 text.
- Refreshed the `build_deck.py` usage docstring and `deck_layout.yaml` comments (v1-only keys noted).

## [0.7.3] - 2026-10-04

### Fixed

- A narrative's `risk1`/`risk2`/`risk3` titles were used verbatim, so a title without the "Risk N:" lead
  left slides 4-6 unlabelled (only the auto-derived fallback added it). The prefix is now added when missing.

## [0.7.2] - 2026-10-04

### Fixed

- A `risk3.cards[].ids` given as a string (which the narrative shape allows) failed the build with
  `KeyError: 'S'`: the slide indexed the string's first character as a checklist ID. Card `ids` are now
  normalised to a list, as `roadmap` and `risk1.fix` already were.

## [0.7.1] - 2026-10-04

### Fixed

- A narrative with a wrong-typed field (e.g. a list for `risk2.positives` or `roadmap.now[].action`) failed the
  build with a bare `TypeError` that named no field. `narrative.validate` now checks every field's type first and
  reports all offenders together by path (`risk2.positives: expected a string, got a list ...`). Any type error
  that still escapes inside a narrative-driven slide is re-raised as a `NarrativeError` naming the slide.

### Added

- `analyze_checklist` returns a `shape` map of the expected narrative types, and a rule that text fields are
  strings, so a draft is right first time.

## [0.7.0] - 2026-10-04

### Added

- `write_summary` MCP tool (`scripts/write_summary.py`): writes the checklist's Summary sheet deterministically.
  Metadata labels, the five block headers and their single shared style, status counts, per-section tallies and
  the Critical Findings / Other Must-Have rows (ID, Section, Title, Status) are computed from the section sheets,
  so the layout the reader expects no longer depends on which model wrote it. The caller supplies only a one-line
  key point per listed finding (<= 90 chars, dict order = row order) and the ordered recommendations. Bad input
  (missing/extra key point, unknown id, blank status, empty recommendations) fails before the file is touched, and
  the saved sheet is re-read with `read_checklist` and compared before it replaces the original.

### Fixed

- Critical Findings / Other Must-Have blocks are now read with `num_cols=5`, so the `Status` and `Key point`
  columns are no longer dropped. A Summary status that disagrees with the section sheet is now reported (the
  `xfail` test recording this gap is removed).

## [0.6.0] - 2026-10-02

### Added

- `analyze_checklist` MCP tool: returns the facts a v2 narrative must cite (checklist hash and default narrative
  path, counts, ids by status, root-cause groups, quick-win candidates, Needs Review items with suggested owners,
  Not Applicable items, open items, validation rules), so a drafted narrative validates first time.
  Backed by `narrative.scaffold()`.
- A v2 build with no narrative now says so: `narrative_missing` (and `narrative_warning`) in the MCP result, and a
  warning from the CLI and the log. Previously only `narrative_used: null` hinted at it.

## [0.5.0] - 2026-10-02

### Added

- A v2 build with no narrative given uses `<checklist_stem>_narrative.json` beside the checklist when it
  exists, and reports `narrative_used` (MCP result).
- A narrative may carry `checklist_sha256`; if the checklist changed since, the build warns that the prose may
  be stale. `tests/fixtures/narrative_example.json` is a synthetic schema example.

## [0.4.0] - 2026-10-02

### Added

- A v2 deck style (`--style v2`, MCP `style="v2"`): a verdict-first ~20-slide storyline (verdict, instance
  snapshot, three risks, quick wins, what we need from you, roadmap, then an appendix of non-Pass/non-N/A
  findings). The headline is Pass / applicable (N/A excluded); the TOC, section dividers, "Thank You" and
  generator-version line are dropped. v2 is the default; `--style v1` / `style="v1"` keeps the previous deck unchanged.
- `scripts/deck_analysis.py`: applicable denominator, notes parser (headline / evidence / Action), root-cause
  grouping, quick-win classifier (Fail + single setting), Needs Review split by owner keywords, N/A groups,
  and a warning when the checklist's own recommendations cite a Pass or N/A item.
- Optional `narrative.json` (`--narrative`, MCP `narrative_path`) for the human-judgment text. It is validated
  in `scripts/narrative.py`: cited IDs must exist and their status must support the claim (a Pass item needs an
  explicit `caveats` entry), risk-tile figures must appear in the cited row, owner groups must equal the Needs
  Review total. Omitted keys fall back to text derived from checklist cells.
- The MCP build tool also returns `slide_count`, `applicable_count`, `pass_count`, `quick_wins` and
  `owner_groups` for v2 builds.
- `config/deck_layout.yaml` `v2:` block (row cap, title truncation, owner keywords).

### Changed

- `python-pptx` is now a dependency, used only by the v2 module. The raw-OOXML rule still governs the v1 path.

## [0.3.1] - 2026-10-02

### Fixed

- The Other Must-Have Items slides no longer carry 3 empty trailing columns. They came from the 6-column
  table template; `make_table_slides()` now drops them (`drop_cols`, `tables.delete_columns()`) and the ID/
  Title/Status columns take the full width.

## [0.3.0] - 2026-10-02

### Changed

- The checklist item sheets now carry a `statement_short` column (right after `statement`), written by
  the checklist generator. `read_checklist.REQUIRED_ITEM_COLUMNS` requires it, so a checklist without the
  column is rejected with `ChecklistFormatError`.
- The findings table's `Statement` column and the critical-finding cards show `statement_short`
  (via `ChecklistItem.slide_statement`), falling back to the full `statement` when it's empty. Speaker
  notes still carry the full statement.

## [0.2.0] - 2026-10-02

### Changed

- The findings table's last column (now headed `Notes`) shows the checklist's `notes` column
  instead of `evidence_found` + `notes` joined, so slides carry the crisp, bulleted summary the
  checklist-review skill now writes. Falls back to `evidence_found` when `notes` is empty. The
  full `evidence_found` and `notes` still go to the slide's speaker notes, as separate lines.
- Table cells render a multi-line value as one paragraph per line (a raw newline in a single
  run doesn't break the line in PowerPoint), and the font-fit heuristic counts each line.

## [0.1.6] - 2026-10-02

### Added

- A pytest suite under `tests/` (`python3 -m pytest`; config in `pytest.ini`, dev dependencies in
  `requirements-dev.txt`). It covers checklist parsing, every `data_warnings` check, the v0.1.4/v0.1.5
  fixes as regression tests, `validate_deck` problem classes, MCP error surfacing, and a golden deck
  snapshot. The snapshot is skipped when the branding template is absent.
- An `xfail` test recording a known gap: Critical Findings / Other Must-Have blocks are read with
  `num_cols=3`, so a `Status` column in the 4th position (the checklist-review skill's standard
  `ID | Section | Title | Status | Key point` layout) is never compared against the section sheets.

## [0.1.5] - 2026-09-30

### Fixed

- The Findings & Risks chapter divider said "0 checklist items assessed" when the Summary sheet's
  Overall Status Counts block had no `Total` row. It now uses the section sheets' item count, the
  same number the Executive Summary shows. A `Total` row that disagrees with that count is reported
  in `data_warnings`.
- Critical Findings cards and the Executive Summary's Top-risk callout showed no section when the
  Summary sheet's Critical Findings block had no `Section` column. Section now falls back to the
  display name of the ID's section sheet, with one warning per block.
- Critical Findings cards showed Excel-truncated section names (e.g. "Advanced Security Options (DSS")
  when the Summary block did have a `Section` column. The card now always shows the curated display
  name of the ID's section sheet, using the block's own text only for an ID no section sheet holds.

## [0.1.4] - 2026-09-30

### Fixed

- A section sheet whose tab name had stray whitespace (e.g. the default template's
  `"Advanced Security Options (DSS "`, trailing space) showed all zeros in the Results by Section
  scorecard. `parse_section_breakdown()` strips the Summary sheet's section names, but
  `build_scorecard_rows()` looked them up by the raw tab name. Both sides are now normalized.
- Critical Findings / Other Must-Have Items silently showed blank titles, and every Other Must-Have
  item as "Needs Review", when the Summary block had no column named exactly `Title`/`Status` (the
  sample checklist's Other Must-Have block has no Status column at all, so Partial items were mislabeled).
  Missing fields now fall back to that ID's own `title`/`validation_status` from its section sheet, with
  one warning per block; the hard-coded "Needs Review" default is gone.
- Long checklist IDs wrapped mid-code in narrow table ID columns in renderers that ignore `wrap="none"`
  on table cells (e.g. LibreOffice). The ID column is now widened to fit the longest ID (up to a cap,
  taken from a prose column), and any ID still too long shrinks its own font; card IDs step down from
  12pt likewise.

### Added

- `data_warnings` in `build_platform_review_deck`'s MCP result (and printed by the CLI): Summary-vs-
  section-sheet consistency checks that structural validation can't catch — scorecard totals vs.
  Overall Status Counts, sections missing from the Per-Section Breakdown, Summary IDs not found in any
  section sheet or with a disagreeing status, unrecognized status labels, uncurated section names.
- `config/section_names.yaml` entry for the "Advanced Security Options (DSS …" section (displayed as
  "Advanced Security Options", order 5) — previously shown via the title-cased fallback as
  "Advanced Security Options (Dss".

## [0.1.3] - 2026-09-28

### Fixed

- The Methodology slide's ("How this Dataiku Platform Review was conducted") divider line cut through
  its intro sentence's text box. Root cause: that slide is cloned from the branding master's "Basic
  slide – Full text" layout, whose intro text box, divider line, and body paragraph box all keep the
  Google-Slides-authored geometry sized for the template's own short Lorem Ipsum placeholder text;
  `build_methodology_slide()` only ever substituted the text runs, never the shape geometry, so the
  real (longer) substituted sentence wrapped to more lines than the box was sized for and rendered
  straight through the divider line below it.
- The same slide's intro/divider/body content additionally sat visibly low in the slide, under a large
  leftover gap below the subtitle inherited from the same template.

  Both fixed together: `build_methodology_slide()` now grows the intro box to fit the real sentence's
  wrap, then recenters the intro/divider/body block as one group within the slide (preserving the
  template's own internal gaps between them), via a new reusable `office.text.set_shape_bounds()`
  helper (id-scoped `<a:off>`/`<a:ext>` setter, mirroring `office.tables.set_graphic_frame_bounds()`).

## [0.1.2] - 2026-09-27

### Fixed

- The Executive Summary slide's "N checklist items assessed across M sections" caption sat inside the
  KPI tile row's vertical span and was painted behind the tiles, so it was hidden. Root cause:
  `build_deck.py`'s `build_exec_summary_kpi_slide()` positioned the caption at a hardcoded
  `CONTENT_TOP + 800400` offset that didn't account for `KPI_ROW_Y`. The caption's y-position is now
  computed from `KPI_ROW_Y` itself (via new `EXEC_SUMMARY_CAPTION_HEIGHT`/`EXEC_SUMMARY_CAPTION_GAP`
  constants), so it always sits in the clear space above the tiles.

## [0.1.1] - 2026-09-27

### Fixed

- Critical Findings card slides (and the Executive Summary's "Top risk" callout) showed only each
  finding's Section name and no indication of what the check actually was. Root cause:
  `read_checklist.py` read the Summary sheet's "Critical Findings" block with `num_cols=2`, silently
  dropping the block's own `Title` column (the sheet is `ID | Section | Title`, same layout as "Other
  Must-Have Items", which already read `num_cols=3` correctly). Cards now show the check's Title as
  the bold headline with Section as supporting context beneath it.

## [0.1.0] - 2026-09-27

### Added

- First versioned release. Introduces the versioning mechanism itself (`VERSION` file,
  `common.VERSION`, `--version` flags, MCP server version metadata, and a version stamp on the
  title slide of every generated deck).
- Everything else — the checklist-to-deck generator (`build_deck.py`), structural validator
  (`validate_deck.py`), and MCP server wrapper (`mcp_server.py`) — predates versioning and is
  captured here as the 0.1.0 baseline.
