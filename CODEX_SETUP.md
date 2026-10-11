# Codex setup

This repository can be installed as a local Codex plugin while keeping its Claude plugin files intact. Codex uses the root `plugin.json` and `mcp.json`; `.codex-plugin/plugin.json` is a compatibility manifest. Both configurations load the task skills and run the review-generator MCP server.

## Install

From this repository, run `codex plugin marketplace list`. Codex may already discover the existing `dataiku-local` marketplace from `.claude-plugin/marketplace.json`. If it does not, run `codex plugin marketplace add /absolute/path/to/this/repo`. Then run `codex plugin add dataiku-diagnosis-toolkit@dataiku-local` and start a new Codex session.

The plugin launches one local stdio MCP server (the review generator). It needs `bash` and Python 3.10+. If the system `python3` is older, set `DATAIKU_PYTHON` to a 3.10+ interpreter; if the review generator tools (`write_summary` etc.) are missing, read `launcher.log` in the plugin-data directory, and use the manual Summary fallback meanwhile. The Codex launcher mirrors only the server source into Codex's writable `PLUGIN_DATA` directory and runs the existing launch script there. The first launch installs dependencies in that directory.

## Branding template

Branded deck generation requires `Dataiku Branding Template 2026.pptx`. This 134 MB file is gitignored and is **not included in a fresh GitHub checkout or GitHub-sourced plugin install**. If it is unavailable, the deck-builder skill asks for its path first, then can generate a standard, unbranded v2 deck with `allow_standard_deck=true`. The Codex launcher links its runtime `resources/` directory to the installed plugin's `mcp-server-review-generator/resources/` directory, which is where the deck tool looks by default.

For the default lookup, copy the template to:

```text
~/.codex/plugins/cache/<marketplace>/dataiku-diagnosis-toolkit/<version>/mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx
```

Use the marketplace and version shown by `codex plugin list` (the local marketplace in this repo is `dataiku-local`). If you install from a local clone that already contains the template, check this cache location first: the local install may already have copied it.

The cache can be replaced when you reinstall or update the plugin. For a durable location, keep the template outside the plugin cache and provide its absolute path in the `base_deck_path` argument when asking Codex to build a deck. Do not place the template in `PLUGIN_DATA`; that directory holds the server runtime, and its `resources/` entry points back to the installed plugin.

## Verify

In a new session, ask Codex to use `dataiku-diagnosis-reader` on an extracted test bundle. There is no reader MCP server: Codex should read the skill's `SKILL.md` and `references/` directly, run `scripts/orient.sh <bundle_root>` with the shell for triage, and run `scripts/peek.py` through the shell to inspect config JSON. It can use normal read/search tools for other bundle files under the reader's guidance. To check the bundled checklist fallback, ask for a diagnosis review without supplying a checklist, then confirm that Codex offers the default template, saves a completed workbook outside the plugin directory, and uses `write_summary` to populate its Summary sheet. Confirm that the review runs `scripts/run_step.py` for orient and facts, writes its run manifest beside the workbook, and ends with `RUN VERIFY: PASS`. For a completed checklist, ask it to use `dataiku-review-deck-builder`; it should have `analyze_checklist`, `build_platform_review_deck`, and `validate_deck`. Confirm that Codex analyzes the final checklist, saves the narrative beside it, and reports a populated `narrative_used` after the v2 build. With no branding template available, confirm that it first asks for the template path, then uses the standard v2 fallback only when appropriate and reports `branded=false` and `base_deck_used=standard`. The `dataiku-codex-workflow` companion explains Codex-specific tool and file-access differences without changing the original task skills.

Local plugins install into a Codex cache. Refresh or reinstall the plugin after changing this repository, then use a new session to load the updated skills and tools.
