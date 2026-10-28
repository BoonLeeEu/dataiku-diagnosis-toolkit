"""The log-review skill, its catalogue and the workbook tool stay in step: the layout the skill documents is the layout
write_log_workbook writes, every catalogue entry is complete, and the confidence words match what the tool accepts."""

import re

import pytest

import mcp_server
import write_log_workbook as wlw
from conftest import REPO_ROOT

SKILL = REPO_ROOT / "skills" / "dataiku-diagnosis-log-review"
CATALOGUE = (SKILL / "references" / "error-catalogue.md").read_text(encoding="utf-8")
LAYOUT = (SKILL / "references" / "workbook-layout.md").read_text(encoding="utf-8")
SKILL_MD = (SKILL / "SKILL.md").read_text(encoding="utf-8")
FIELDS = ("Signature", "Cause", "Confidence", "Check next", "Mitigation")


def entries():
    parts = re.split(r"^### (LOG-[A-Z]+-\d{3}) (.+)$", CATALOGUE, flags=re.M)
    return [(parts[i], parts[i + 1], parts[i + 2]) for i in range(1, len(parts), 3)]


def test_catalogue_has_entries_with_unique_ids():
    ids = [e[0] for e in entries()]
    assert len(ids) >= 20 and len(ids) == len(set(ids))


@pytest.mark.parametrize("entry", entries(), ids=lambda e: e[0])
def test_every_entry_is_complete(entry):
    _, _, body = entry
    for field in FIELDS:
        assert re.search(rf"^- \*\*{field}:\*\*", body, re.M), f"{entry[0]} lacks {field}"
    assert re.search(r"^  1\. ", body, re.M), f"{entry[0]} mitigation has no numbered steps"
    assert re.search(r"Confirmed|Likely|Unknown", body.split("**Confidence:**", 1)[1].split("\n", 1)[0])


def test_entries_only_cite_entries_that_exist():
    ids = {e[0] for e in entries()}
    cited = set(re.findall(r"LOG-[A-Z]+-\d{3}", CATALOGUE))
    assert cited <= ids, sorted(cited - ids)


def test_the_documented_layout_names_every_column_and_sheet_the_tool_writes():
    for header, _ in wlw.LOG_COLUMNS:
        if header not in ("Level", "Count", "ID"):  # short words appear everywhere; the long ones prove the table is documented
            assert header in LAYOUT, header
    for header in ("Logs scanned", "Findings", "Not in bundle", "Go to details", "Back to Overview"):
        assert header in LAYOUT, header
    assert wlw.OVERVIEW in LAYOUT


def test_the_skill_uses_the_same_confidence_and_level_words_as_the_tool():
    for word in wlw.CONFIDENCES:
        assert word in LAYOUT and word in SKILL_MD, word
    for word in wlw.LEVELS:
        assert word in LAYOUT, word


def test_the_skill_names_a_tool_the_server_actually_registers():
    assert "write_log_workbook" in SKILL_MD and hasattr(mcp_server, "write_log_workbook")


def test_the_skill_points_at_files_that_exist():
    for name in re.findall(r"`(references/[\w.-]+\.md)`", SKILL_MD):
        assert (SKILL / name).is_file(), name
    reader = REPO_ROOT / "skills" / "dataiku-diagnosis-reader"
    assert (reader / "scripts" / "logscan.py").is_file() and (reader / "references" / "logs.md").is_file()
