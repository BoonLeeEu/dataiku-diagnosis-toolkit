#!/usr/bin/env python3
"""MCP (Model Context Protocol) stdio server exposing this repo's deck tools
(build, validate, analyze_checklist, write_summary) to MCP
clients (Claude Desktop, Claude Code, other MCP-capable LLM tools).

Built against the mcp>=2.0 SDK's MCPServer (the renamed successor to 1.x's
FastMCP -- same decorator-based API, see mcp's own v2 migration guide).

Launch directly, e.g. from an MCP client config:
    python3 <repo>/scripts/mcp_server.py

This is a thin wrapper: it resolves the same defaults build_deck.py's own
main() resolves (config/deck_layout.yaml fallbacks, default_output_path()),
then calls build_deck.build_deck() / validate_deck.validate() unchanged.
"""

import functools
import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import common
import styles
import validate_deck as validate_deck_lib

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

# Keep stdout reserved for the MCP JSON-RPC channel; progress logs go to stderr,
# which MCP clients typically surface as server logs.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)

mcp = MCPServer("dataiku-review-generator", version=common.VERSION)


def _resolve(p: str) -> Path:
    """Resolve a path against the repo root, not this server process's CWD
    (an MCP client config doesn't reliably control the launched process's
    working directory)."""
    path = Path(p)
    return path if path.is_absolute() else (common.REPO_ROOT / path).resolve()


def _mtime(path) -> str | None:
    """File modification time as UTC ISO text, or None if there is no such file. Lets a caller notice
    that the file this server read on the device is not the one it just wrote elsewhere."""
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return None


def _surface_errors(fn):
    """mcp.server.mcpserver treats any raised exception other than ToolError as an
    unanticipated crash and hides its message from the caller (the client only sees
    "Error executing tool <name>"). This repo's errors (missing files, a checklist
    failing schema validation, ...) are deliberately clear, fail-fast messages meant
    to be read by whoever's driving the tool -- re-raise them as ToolError so that
    message actually reaches the calling LLM."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(str(e)) from e
    return wrapper


@mcp.tool()
@_surface_errors
def build_platform_review_deck(
    checklist_path: str,
    customer: str,
    logo_path: str | None = None,
    output_path: str | None = None,
    rows_per_slide: int | None = None,
    include_pass_items: bool | None = None,
    base_deck_path: str | None = None,
    style: str = styles.DEFAULT_STYLE,
    narrative_path: str | None = None,
    allow_standard_deck: bool = False,
) -> dict[str, Any]:
    """Generate a branded Dataiku Platform Review .pptx deck from a completed
    checklist workbook, writing it to disk and returning its path.

    Mirrors `python3 scripts/build_deck.py`. Runs the same structural
    validation automatically afterward (see the validate_deck tool) and
    reports any problems found, rather than requiring a separate call.

    Args:
        checklist_path: Path to a completed checklist .xlsx (required).
            A relative path is resolved against this repo's root, not this
            server process's working directory.
        customer: Customer name, shown verbatim (upper-cased) on the title
            slide (required).
        logo_path: Optional path to a customer logo image, spliced into the
            title slide. Omit to leave the title slide without a logo.
        output_path: Output .pptx path. Defaults to
            "output/<Customer_Slug>_Platform_Review_<date>.pptx", where
            <date> is a YYYY-MM-DD found in the checklist filename, else
            today's date.
        rows_per_slide: Max table rows per findings slide. Defaults to
            config/deck_layout.yaml's table_rows_per_slide (4 if unset).
        include_pass_items: Also list Pass/Not-Applicable items in findings
            tables, not just Fail/Partial/Needs Review. If omitted, uses
            config/deck_layout.yaml's include_pass_items (default true).
            Unlike the CLI's --include-pass-items flag (which can only turn
            this on for a run), passing an explicit false here overrides a
            true config default for this call.
        base_deck_path: Base branded .pptx to build from. Defaults to
            "resources/Dataiku Branding Template 2026.pptx".
        style: "v2" (default; the verdict-first ~20-slide storyline: verdict,
            instance snapshot, three risks, quick wins, what we need from
            you, roadmap, then an appendix) or "v1" (one findings slide per
            few items). v2 ignores rows_per_slide/include_pass_items.
        narrative_path: v2 only. Optional narrative.json with the
            human-judgment text (verdict, takeaways, risks, roadmap...).
            If omitted, a file named <checklist_stem>_narrative.json beside the
            checklist is used when present. Every cited ID must exist and its status must support the
            claim, or the call fails with a specific error. Omitted keys
            fall back to text derived from checklist cells.
        allow_standard_deck: v2 only. When the branding template is missing,
            build a standard, UNBRANDED deck (same slides, plain cover, no
            Dataiku template) instead of failing. Default false: pass true
            only after asking the user for the template and being told there
            is none. Ignored when the template is found, and when base_deck_path is given
            (a wrong explicit path is an error, not a fallback).

    Returns:
        A dict with:
          - output_path: absolute path to the generated .pptx
          - structural_problems: list of structural-validation problem
            strings (empty list means the deck passed all automated checks)
          - data_warnings: list of checklist data inconsistencies (e.g.
            section totals that don't match Overall Status Counts, Summary
            rows whose ID/status disagree with the section sheets) -- the
            deck still built, but may show wrong or missing values; fix the
            checklist and rebuild rather than patching the deck
          - manual_qa_checklist: guidance for the manual visual QA pass that
            automated validation cannot perform (only present when
            structural_problems is empty)
          - base_deck_used ("template" or "standard") and branded (false for a
            standard deck): say so when handing the deck over
          - generator_version: this tool's own version (common.VERSION) that
            produced the deck
          - checklist_path, checklist_modified: the resolved path actually read and its
            UTC modified time (compare with what you last wrote)
          - v2 adds slide_count, narrative_used (path or null), narrative_modified (its UTC modified time or null),
            narrative_missing (true when no narrative was used; the deck's
            judgment text is then generic, derived from cells) and, when
            missing, narrative_warning, plus applicable_count, pass_count,
            quick_wins and owner_groups
    """
    layout_config = common.load_config("deck_layout.yaml")

    checklist = _resolve(checklist_path)
    env_template = os.environ.get(common.BASE_DECK_ENV, "").strip()
    base_deck = (
        _resolve(base_deck_path) if base_deck_path
        else _resolve(env_template) if env_template
        else common.REPO_ROOT / layout_config.get("base_deck", common.DEFAULT_BASE_DECK)
    )
    logo = _resolve(logo_path) if logo_path else None
    effective_rows_per_slide = rows_per_slide if rows_per_slide is not None else layout_config.get("table_rows_per_slide", common.DEFAULT_ROWS_PER_SLIDE)
    effective_include_pass_items = (
        include_pass_items if include_pass_items is not None
        else layout_config.get("include_pass_items", True)
    )
    resolved_output = _resolve(output_path) if output_path else common.default_output_path(checklist, customer)

    if not checklist.exists():
        raise FileNotFoundError(f"Checklist file not found: {checklist}")
    standard_deck = False
    if not base_deck.exists():
        if not (allow_standard_deck and style == "v2" and not base_deck_path):
            hint = (
                "Supply the Dataiku Branding Template with base_deck_path, or call again with "
                "allow_standard_deck=true for a standard unbranded deck (style v2 only)."
                if style == "v2" else
                "Supply the Dataiku Branding Template with base_deck_path; style v1 has no unbranded fallback "
                "(style v2 does)."
            )
            setup = (
                f" To set it up once: put the template at {common.DEFAULT_BASE_DECK} in the plugin, or set "
                f"{common.BASE_DECK_ENV} to its absolute path (see the README's \"One-time setup\")."
            )
            raise FileNotFoundError(f"Base deck not found: {base_deck}. {hint}{setup}")
        standard_deck = True
    if logo is not None and not logo.exists():
        raise FileNotFoundError(f"Logo file not found: {logo}")

    styles.get_style(style)  # unknown style -> ValueError naming the valid ones
    narrative = _resolve(narrative_path) if narrative_path else None
    if narrative is not None and not styles.get_style(style).accepts_narrative:
        raise ValueError(f"narrative_path does not apply to style={style!r}")

    built = styles.build(style, styles.BuildRequest(
        checklist_path=checklist, customer=customer, output_path=resolved_output, base_deck=base_deck,
        logo_path=logo, narrative_path=narrative, rows_per_slide=effective_rows_per_slide,
        include_pass_items=effective_include_pass_items, standard_deck=standard_deck,
    ))
    resolved_output = built["output_path"]
    extras = {k: v for k, v in built.items() if k not in ("output_path", "warnings")}

    try:
        problems = validate_deck_lib.validate(resolved_output)
    except Exception as e:
        raise RuntimeError(f"Deck was generated at {resolved_output} but structural validation failed to run: {e}") from e

    result = {
        "output_path": str(resolved_output),
        "structural_problems": problems,
        "data_warnings": built["warnings"],
        "generator_version": common.VERSION,
        "checklist_path": str(checklist),
        "checklist_modified": _mtime(checklist),
    }
    result.update({
        "base_deck_used": "standard" if standard_deck else "template",
        "branded": not standard_deck,
    })
    if extras:
        result.update(extras)
        if "narrative_used" in extras:
            result["narrative_modified"] = _mtime(extras["narrative_used"]) if extras["narrative_used"] else None
        if extras.get("narrative_missing"):
            import narrative as narrative_mod
            result.update({"narrative_warning": narrative_mod.MISSING_WARNING})  # not a base return key
    if not problems:
        result["manual_qa_checklist"] = validate_deck_lib.manual_qa_checklist(style)
        if standard_deck:
            result["manual_qa_checklist"] += (
                "\nThis is the standard layout, not the Dataiku-branded deck: do not present it as branded. "
                "To brand it, supply the template and rebuild from the same checklist and narrative."
            )
    return result


@mcp.tool()
@_surface_errors
def write_summary(
    checklist_path: str,
    reviewer: str,
    bundle: str,
    key_points: dict[str, str],
    recommendations: list[str],
    node_version: str = "",
    diagnosis_generated: str = "",
) -> dict[str, Any]:
    """Write (or recreate) the Summary sheet of a reviewed checklist, in the exact
    layout the deck generator reads. Call it once every item's validation_status is
    filled in and before analyze_checklist (the narrative's checklist hash pins the
    final file). Counts, per-section tallies and the finding rows are computed from
    the section sheets; you supply only the judgment text.

    Args:
        checklist_path: Path to the reviewed checklist .xlsx (required). A relative
            path is resolved against this repo's root. The file is updated in place.
        reviewer: Reviewer name for the Reviewer: row (required).
        bundle: Diagnosis bundle name for the Bundle: row (required).
        key_points: {item id: one-line key point, <= 90 chars} for EVERY must-have
            item that is Fail, Partial or Needs Review, and no others. Key order sets
            the order within each block: Fail items listed most causally central first.
        recommendations: Ordered actions, root cause before its symptoms. Numbering
            ("1. ") is added for you.
        node_version: Node / Version: row, e.g. "Design node / 14.4.3".
        diagnosis_generated: Diagnosis generated: row (date as in the bundle).

    Returns:
        A dict with checklist_path, counts (per status and Total), sections,
        critical_findings, other_must_have and recommendations (counts of rows written).
        Fails with a message naming the problem (missing key point, unknown id, blank
        status, ...) without touching the file; the saved sheet is re-read the way the
        deck generator reads it before it replaces the file.
    """
    import write_summary as write_summary_lib

    checklist = _resolve(checklist_path)
    if not checklist.exists():
        raise FileNotFoundError(f"Checklist file not found: {checklist}")
    return write_summary_lib.write_summary(
        checklist,
        reviewer=reviewer,
        bundle=bundle,
        node_version=node_version,
        diagnosis_generated=diagnosis_generated,
        key_points=key_points,
        recommendations=recommendations,
        config=common.load_config("section_names.yaml"),
    )


@mcp.tool()
@_surface_errors
def analyze_checklist(checklist_path: str) -> dict[str, Any]:
    """Read a completed checklist and return the facts a v2 narrative must cite,
    so Claude can draft <checklist_stem>_narrative.json that validates first time.
    Read-only; builds no deck. Call it after the checklist is final.

    Args:
        checklist_path: Path to a completed checklist .xlsx (required). A
            relative path is resolved against this repo's root.

    Returns:
        A dict with checklist_sha256 (record it in the narrative), narrative_path
        (where to save it), counts/total/applicable, per-section counts,
        ids_by_status, root_cause_groups, quick_win_candidates,
        remaining_fails, needs_review (each with a suggested_owner; owner
        groups must cover them all once), not_applicable (na_groups must cover
        them all once), open_items (Fail/Partial, with headline and action),
        checklist_path (resolved path read), checklist_modified, narrative_exists and
        narrative_modified (for the file at narrative_path, so a stale copy is visible), rules (the
        narrative's validation constraints), shape (the narrative's exact keys and
        types, with the allowed values of tone, state and effort spelled out) and warnings.
    """
    import deck_analysis
    import narrative
    import read_checklist
    import section_names

    checklist = _resolve(checklist_path)
    if not checklist.exists():
        raise FileNotFoundError(f"Checklist file not found: {checklist}")
    section_config = common.load_config("section_names.yaml")
    layout_config = common.load_config("deck_layout.yaml")
    data = read_checklist.read_checklist(checklist, section_config)
    ordered = section_names.order_sections(data.sheet_tab_names, section_config)
    a = deck_analysis.analyze(data, ordered, layout_config.get("v2", {}))
    result = narrative.scaffold(a, checklist)
    result.update(checklist_path=str(checklist), checklist_modified=_mtime(checklist),
                  narrative_exists=Path(result["narrative_path"]).exists(),
                  narrative_modified=_mtime(result["narrative_path"]))
    return result


@mcp.tool(name="validate_deck")
@_surface_errors
def validate_deck_tool(pptx_path: str) -> dict[str, Any]:
    """Run structural self-checks against an already-generated .pptx deck
    (malformed XML, dangling slide relationships, leftover placeholder
    text). Does not perform layout/visual QA -- see the manual_qa_checklist
    returned by build_platform_review_deck for that.

    Args:
        pptx_path: Path to a .pptx file to validate. A relative path is
            resolved against this repo's root, not this server process's
            working directory.

    Returns:
        A dict with:
          - pptx_path: the resolved absolute path that was checked
          - passed: true if no structural problems were found
          - problems: list of human-readable problem strings (empty if
            passed is true)
          - generator_version: this tool's own version (common.VERSION) that
            ran the validation
    """
    path = _resolve(pptx_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        problems = validate_deck_lib.validate(path)
    except zipfile.BadZipFile as e:
        raise ValueError(f"File is not a valid .pptx (corrupt or wrong format): {path}") from e

    return {
        "pptx_path": str(path),
        "passed": not problems,
        "problems": problems,
        "generator_version": common.VERSION,
    }


if __name__ == "__main__":
    mcp.run()
