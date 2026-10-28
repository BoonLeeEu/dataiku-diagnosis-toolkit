"""mcp_server.py's error surfacing and path resolution. The exact error
messages matter: the dataiku-review-deck-builder skill relays them verbatim
(and keys its "Base deck not found" handling off that wording)."""

import pytest

pytest.importorskip("mcp", reason="mcp SDK not installed (only needed by scripts/mcp_server.py)")

import common  # noqa: E402
from conftest import item  # noqa: E402
import mcp_server  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402


def test_relative_paths_resolve_against_repo_root():
    assert mcp_server._resolve("resources/x.xlsx") == (common.REPO_ROOT / "resources/x.xlsx").resolve()


def test_absolute_paths_are_kept(tmp_path):
    assert mcp_server._resolve(str(tmp_path)) == tmp_path


def test_missing_checklist_surfaces_as_tool_error(tmp_path):
    with pytest.raises(ToolError, match="Checklist file not found"):
        mcp_server.build_platform_review_deck(checklist_path=str(tmp_path / "nope.xlsx"), customer="Acme")


def test_missing_base_deck_surfaces_as_tool_error(checklist_factory, tmp_path):
    with pytest.raises(ToolError, match="Base deck not found"):
        mcp_server.build_platform_review_deck(
            checklist_path=str(checklist_factory()), customer="Acme",
            base_deck_path=str(tmp_path / "missing.pptx"),
        )


def test_missing_logo_surfaces_as_tool_error(checklist_factory, tmp_path):
    base = tmp_path / "base.pptx"
    base.write_bytes(b"")
    with pytest.raises(ToolError, match="Logo file not found"):
        mcp_server.build_platform_review_deck(
            checklist_path=str(checklist_factory()), customer="Acme",
            base_deck_path=str(base), logo_path=str(tmp_path / "logo.png"),
        )


def test_validate_deck_rejects_non_zip(tmp_path):
    bogus = tmp_path / "deck.pptx"
    bogus.write_text("not a zip")
    with pytest.raises(ToolError, match="not a valid .pptx"):
        mcp_server.validate_deck_tool(pptx_path=str(bogus))


def test_validate_deck_missing_file(tmp_path):
    with pytest.raises(ToolError, match="File not found"):
        mcp_server.validate_deck_tool(pptx_path=str(tmp_path / "nope.pptx"))


def test_analyze_checklist_returns_scaffold(checklist_factory):
    path = checklist_factory({"Architecture, Compute & Infrast": [item("ARCH-001", "Fail"), item("ARCH-002", "Not Applicable")]})
    res = mcp_server.analyze_checklist(checklist_path=str(path))
    assert res["counts"]["Fail"] == 1 and len(res["checklist_sha256"]) == 64
    assert [r["id"] for r in res["not_applicable"]] == ["ARCH-002"]


def test_analyze_checklist_reports_resolved_paths_and_narrative_state(checklist_factory):
    path = checklist_factory({"Architecture, Compute & Infrast": [item("ARCH-001", "Fail")]})
    res = mcp_server.analyze_checklist(checklist_path=str(path))
    assert res["checklist_path"] == str(path) and res["checklist_modified"]
    assert res["narrative_exists"] is False and res["narrative_modified"] is None
    path.with_name(path.stem + "_narrative.json").write_text("{}")
    res = mcp_server.analyze_checklist(checklist_path=str(path))
    assert res["narrative_exists"] is True and res["narrative_modified"]


def test_analyze_checklist_missing_file_surfaces_as_tool_error(tmp_path):
    with pytest.raises(ToolError, match="Checklist file not found"):
        mcp_server.analyze_checklist(checklist_path=str(tmp_path / "nope.xlsx"))


def test_write_summary_tool_writes_and_reports(checklist_factory):
    path = checklist_factory()
    res = mcp_server.write_summary(
        checklist_path=str(path), reviewer="A. Reviewer", bundle="synthetic_bundle",
        key_points={"ARCH-002": "Runtime DB is H2.", "ARCH-001": "Sizing unconfirmed.", "SEC-001": "MFA not enforced."},
        recommendations=["Fix ARCH-002 first."],
    )
    assert res["counts"]["Total"] == 6 and res["critical_findings"] == 1 and res["other_must_have"] == 2


def test_write_summary_tool_surfaces_input_errors_as_tool_errors(checklist_factory):
    with pytest.raises(ToolError, match="missing a line"):
        mcp_server.write_summary(
            checklist_path=str(checklist_factory()), reviewer="r", bundle="b", key_points={}, recommendations=["x"],
        )


def test_write_log_workbook_tool_writes_and_reports(tmp_path):
    out = tmp_path / "log_review.xlsx"
    res = mcp_server.write_log_workbook(
        output_path=str(out), bundle="b", reviewer="r",
        logs=[{"id": "backend", "label": "backend.log", "findings": [{
            "id": "backend-001", "level": "ERROR", "pattern": "[dku.x] failed", "count": 2,
            "confidence": "Unknown", "check_next": ["Look at backend.log around the first sighting"]}]}],
    )
    assert out.exists() and res["sheets"] == ["Overview", "backend.log"] and res["by_confidence"]["Unknown"] == 1


def test_write_log_workbook_tool_surfaces_input_errors_as_tool_errors(tmp_path):
    with pytest.raises(ToolError, match="confidence"):
        mcp_server.write_log_workbook(
            output_path=str(tmp_path / "x.xlsx"), bundle="b", reviewer="r",
            logs=[{"id": "backend", "findings": [{"id": "b-1", "level": "ERROR", "pattern": "p", "count": 1,
                                                    "confidence": "Maybe"}]}],
        )
