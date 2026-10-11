"""run_step.py (checklist-review skill): records reader script runs and verifies a finished review."""
import json
import subprocess
import sys

import openpyxl

from conftest import FIXTURES, REPO_ROOT

SCRIPT = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts" / "run_step.py"
BUNDLE = FIXTURES / "bundles" / "synthetic_design_baseline"


def _sh(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def _checklist(path, *, summary=True, total=2):
    wb = openpyxl.Workbook()
    wb.active.title = "Summary" if summary else "Other"
    if summary:
        wb["Summary"].append(["Total", total])
    ws = wb.create_sheet("Section")
    ws.append(["id", "title", "validation_status"])
    ws.append(["A-1", "First check", "Pass"])
    ws.append(["A-2", "Second check", "Fail"])
    wb.save(path)


def _record_both(manifest):
    """Record the two reader steps and the verdicts step (no rules exist for the A-n ids, so nothing is judged)."""
    for step in ("orient", "facts"):
        assert _sh("run", step, BUNDLE, "--manifest", manifest).returncode == 0
    xlsx = manifest.parent / "recorded.xlsx"
    _checklist(xlsx)
    assert _sh("verdicts", BUNDLE, "--manifest", manifest, "--checklist", xlsx).returncode == 0


def test_run_records_steps_and_saves_facts(tmp_path):
    manifest = tmp_path / "r_run_manifest.json"
    _record_both(manifest)
    data = json.loads(manifest.read_text())
    assert set(data["steps"]) == {"orient", "facts", "verdicts"} and data["reader_version"] != "unknown"
    assert all(s["exit_status"] == 0 and len(s["stdout_sha256"]) == 64 for s in data["steps"].values())
    assert "facts" in json.loads((tmp_path / "r_facts.json").read_text())
    assert json.loads((tmp_path / "r_verdicts.json").read_text())["verdicts"] == []  # the fixture checklist matches no rule


def test_verify_passes_on_a_complete_run(tmp_path):
    manifest, xlsx = tmp_path / "r_run_manifest.json", tmp_path / "r.xlsx"
    _record_both(manifest)
    _checklist(xlsx)
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx)
    assert out.returncode == 0 and "PASS" in out.stdout, out.stdout


def test_verify_fails_when_facts_never_ran_or_hash_is_wrong(tmp_path):
    manifest, xlsx = tmp_path / "r_run_manifest.json", tmp_path / "r.xlsx"
    _checklist(xlsx)
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx).stdout
    assert "orient not recorded" in out and "verdicts not recorded" in out
    _record_both(manifest)
    data = json.loads(manifest.read_text())
    data["steps"]["facts"]["stdout_sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx)
    assert out.returncode == 1 and "does not match" in out.stdout


def test_verify_fails_on_missing_or_stale_summary_and_missing_deck(tmp_path):
    manifest = tmp_path / "r_run_manifest.json"
    _record_both(manifest)
    for kwargs, msg in (({"summary": False}, "not Summary"), ({"total": 5}, "stale")):
        xlsx = tmp_path / "x.xlsx"
        _checklist(xlsx, **kwargs)
        out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx)
        assert out.returncode == 1 and msg in out.stdout, out.stdout
    xlsx = tmp_path / "r.xlsx"
    _checklist(xlsx)
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx, "--deck", tmp_path / "d.pptx")
    assert out.returncode == 1 and "missing" in out.stdout


def test_verify_reports_a_bad_checklist_or_manifest_as_a_fail_line_not_a_traceback(tmp_path):
    manifest = tmp_path / "r_run_manifest.json"
    _record_both(manifest)
    bad = tmp_path / "bad.xlsx"
    bad.write_text("not a workbook")
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", bad)
    assert out.returncode == 1 and "cannot open checklist" in out.stdout and "Traceback" not in out.stderr
    manifest.write_text("{not json")
    xlsx = tmp_path / "r.xlsx"
    _checklist(xlsx)
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx)
    assert out.returncode == 1 and "cannot read manifest" in out.stdout and "Traceback" not in out.stderr


def test_run_creates_the_manifest_directory_and_rejects_a_corrupt_manifest(tmp_path):
    manifest = tmp_path / "new" / "dir" / "r_run_manifest.json"
    assert _sh("run", "orient", BUNDLE, "--manifest", manifest).returncode == 0 and manifest.exists()
    manifest.write_text("{not json")
    out = _sh("run", "orient", BUNDLE, "--manifest", manifest)
    assert out.returncode == 2 and "cannot run orient" in out.stderr and "Traceback" not in out.stderr


def test_verify_passes_when_the_bundle_is_at_a_different_path_than_the_run(tmp_path):
    """facts.py prints the absolute bundle path; the recorded hash must not depend on it (staging copies, other machines)."""
    import shutil

    manifest, xlsx = tmp_path / "r_run_manifest.json", tmp_path / "r.xlsx"
    _record_both(manifest)
    _checklist(xlsx)
    moved = tmp_path / "elsewhere" / "copy_of_bundle"
    shutil.copytree(BUNDLE, moved)
    out = _sh("verify", moved, "--manifest", manifest, "--checklist", xlsx)
    assert out.returncode == 0 and "PASS" in out.stdout, out.stdout


def test_verify_still_accepts_a_manifest_hash_recorded_before_the_path_fix(tmp_path):
    import hashlib

    manifest, xlsx = tmp_path / "r_run_manifest.json", tmp_path / "r.xlsx"
    _record_both(manifest)
    _checklist(xlsx)
    raw = (tmp_path / "r_facts.json").read_text()
    data = json.loads(manifest.read_text())
    data["steps"]["facts"]["stdout_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    manifest.write_text(json.dumps(data))
    assert _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx).returncode == 0


def test_plugin_scripts_with_modern_annotations_defer_them():
    """`X | None` annotations crash on Python <3.10 unless deferred; the plugin supports older system pythons for these scripts."""
    import re
    root = REPO_ROOT / "skills"
    bad = [str(p.relative_to(root)) for p in root.glob("*/scripts/*.py")
           if re.search(r"\) -> [^\n]*\| None|: [\w\[\], .]*\| None", p.read_text())
           and "from __future__ import annotations" not in p.read_text()]
    assert not bad, bad


def _run_step_module():
    sys.path.insert(0, str(SCRIPT.parent))
    import run_step
    return run_step


def _fake_python(path):
    path.parent.mkdir(parents=True)
    path.write_text("")
    return path


def test_venv_pythons_search_order(tmp_path, monkeypatch):
    rs = _run_step_module()
    own = _fake_python(tmp_path / "own" / "python3")
    data = _fake_python(tmp_path / "data" / "review-generator" / rs.VENV_PYTHON)
    old = _fake_python(tmp_path / "home" / ".codex/plugins/data/m/aaa/review-generator" / rs.VENV_PYTHON)
    new = _fake_python(tmp_path / "home" / ".codex/plugins/data/m/bbb/review-generator" / rs.VENV_PYTHON)
    import os
    os.utime(old, (1, 1))
    monkeypatch.setenv("DATAIKU_PYTHON", str(own))
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "data"))
    found = rs.venv_pythons(home=tmp_path / "home")
    assert [p for p in found if str(p).startswith(str(tmp_path))] == [own, data, new, old]


def test_missing_openpyxl_without_a_venv_exits_with_the_fix(monkeypatch):
    rs = _run_step_module()
    real = __import__
    monkeypatch.setattr("builtins.__import__", lambda n, *a, **k: (_ for _ in ()).throw(ImportError()) if n == "openpyxl" else real(n, *a, **k))
    monkeypatch.setattr(rs, "venv_pythons", lambda home=None: [])
    try:
        rs.ensure_openpyxl()
    except SystemExit as e:
        assert "DATAIKU_PYTHON" in str(e.code) and "openpyxl" in str(e.code)
    else:
        raise AssertionError("expected SystemExit")
