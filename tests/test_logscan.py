"""The reader's logscan.py groups each log's errors and warnings, keeps windows and pointers, and never leaks.

Runs it on a synthetic bundle built into tmp_path (tests/lib/log_bundle.py), never a real one. The planted names,
addresses and secrets in that bundle must not appear anywhere in the output: the masking is the contract that lets a
workbook quote an excerpt."""

import functools
import json
import subprocess
import sys

import pytest

import log_bundle
from conftest import REPO_ROOT

LOGSCAN = REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "logscan.py"


def scan(root, *args):
    proc = subprocess.run([sys.executable, "-I", str(LOGSCAN), str(root), *args], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout), proc.stdout


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return scan(log_bundle.build(tmp_path_factory.mktemp("bundle")))


@pytest.fixture
def logs(result):
    return result[0]["logs"]


def by_pattern(log, needle):
    return next(f for f in log["findings"] if needle in f["pattern"])


def test_every_log_is_present_and_scanned(logs):
    assert set(logs) == {"backend", "frontend", "nginx", "ipython", "eventserver", "supervisord", "install",
                         "install-impersonation", "codeenv", "dmesg", "stacks", "hs_err"}
    assert all(v["present"] and "error" not in v for v in logs.values())


def test_planted_identifiers_never_reach_the_output(result):
    text = result[1]
    for leak in log_bundle.LEAKS:
        assert leak not in text, leak


def test_backend_groups_repeats_and_counts_each_level_in_its_own_position(logs):
    b = logs["backend"]
    assert b["totals"] == {"WARN": 1, "ERROR": 7, "FATAL": 0}  # the quoted "[ERROR]" in an INFO line is not counted; the INFO OOM line is
    jobs = by_pattern(b, "Job '<x>' failed")
    assert jobs["count"] == 3 and jobs["files_affected"] == 2
    assert jobs["first"] == "2026/01/01-01:00:00" and jobs["last"] == "2026/01/03-01:05:00"


def test_backend_windows_follow_rotation_order_and_gz_is_skipped(logs):
    b = logs["backend"]
    assert [f["file"] for f in b["files"]] == ["run/backend.log.1", "run/backend.log"]
    assert b["files"][0]["first"] == "2026/01/01-00:00:01" and b["files"][1]["last"] == "2026/01/03-04:00:00"
    assert b["gz_files_skipped"] == 1


def test_first_seen_pointer_names_the_file_and_line(logs):
    f = by_pattern(logs["backend"], "Job")
    assert f["first_seen_at"] == "run/backend.log.1:2"


def test_excerpt_keeps_the_line_and_its_continuation_and_cause(logs):
    f = by_pattern(logs["backend"], "Kernel crashed")
    assert any("at com.dataiku.dip.Foo.run" in line for line in f["excerpt"])
    assert any(line.startswith("Caused by:") for line in f["excerpt"])


def test_out_of_memory_lines_count_as_errors_whatever_their_level(logs):
    f = by_pattern(logs["backend"], "Task died")
    assert f["level"] == "ERROR" and "OutOfMemoryError" in " ".join(f["excerpt"])


def test_masking_leaves_placeholders_in_excerpts(logs):
    text = json.dumps(logs["backend"])
    for placeholder in ("<user>", "<ip>", "<email>", "<secret>", "<project>"):
        assert placeholder in text, placeholder


def test_findings_are_ordered_by_severity_then_count(logs):
    n = logs["nginx"]["findings"]
    keys = [({"FATAL": 0, "ERROR": 1, "WARN": 2}[f["level"]], -f["count"]) for f in n]
    assert keys == sorted(keys) and n[0]["level"] == "FATAL"


def test_nginx_error_log_alert_preamble_and_emerg(logs):
    n = logs["nginx"]
    assert n["totals"]["FATAL"] == 1 and n["totals"]["ERROR"] == 3
    refused = by_pattern(n, "Connection refused")
    assert refused["count"] == 2 and refused["first"] == "2026/01/03-04:00:00"
    assert by_pattern(n, "could not open error log file")["first"] == "ABSENT"  # a preamble line has no timestamp


def test_ipython_warning_level_counts_as_warn(logs):
    i = logs["ipython"]
    assert i["totals"] == {"WARN": 1, "ERROR": 1, "FATAL": 0}


def test_supervisord_serious_events_are_rated_above_their_log_level(logs):
    s = logs["supervisord"]
    levels = {f["pattern"]: f["level"] for f in s["findings"]}
    assert any("gave up" in p and lvl == "ERROR" for p, lvl in levels.items())
    assert any("not expected" in p and lvl == "ERROR" for p, lvl in levels.items())
    assert any("killing" in p and lvl == "WARN" for p, lvl in levels.items())
    assert not any("started" in p for p in levels)


def test_clean_logs_report_zero_findings(logs):
    for name in ("eventserver", "install-impersonation"):
        assert logs[name]["totals"] == {"WARN": 0, "ERROR": 0, "FATAL": 0} and logs[name]["findings"] == []


def test_install_log_finds_real_failures_not_the_yarn_noise_as_errors(logs):
    i = logs["install"]
    patterns = [f["pattern"] for f in i["findings"] if f["level"] == "ERROR"]
    assert any("Traceback" in p for p in patterns) and any("Failed to migrate" in p for p in patterns)
    assert any("permission denied for schema" in p or "PSQLException" in p for p in patterns)
    assert by_pattern(i, "to launch YARN applications")["level"] == "WARN"  # quoted text is normalised away


def test_code_env_logs_separate_retries_from_failures(logs):
    c = logs["codeenv"]
    assert by_pattern(c, "Retrying")["level"] == "WARN"
    assert by_pattern(c, "No matching distribution")["level"] == "ERROR"
    assert c["files"][0]["first"] == "ABSENT"  # a pip transcript has no timestamps


def test_kernel_oom_and_blocked_tasks_in_dmesg(logs):
    d = logs["dmesg"]
    assert by_pattern(d, "out of memory")["level"] == "ERROR"
    assert any(f["level"] == "WARN" and "blocked" in f["pattern"] for f in d["findings"])


def test_stacks_reports_blocked_threads_deadlocks_and_state_counts(logs):
    s = logs["stacks"]
    assert any(f["level"] == "WARN" and f["pattern"].startswith("Thread BLOCKED") for f in s["findings"])
    assert any(f["pattern"] == "Java-level deadlock" and f["level"] == "ERROR" for f in s["findings"])
    assert s["thread_states"] == {"BLOCKED": 1, "RUNNABLE": 1}


def test_hs_err_is_fatal_with_its_class_process_and_time(logs):
    f = logs["hs_err"]["findings"][0]
    assert f["level"] == "FATAL" and "Out of Memory Error" in f["pattern"] and "DSSBackendMain" in f["pattern"]
    assert f["first"].startswith("Sat Jan")


def test_no_excerpts_drops_all_log_text(tmp_path):
    data, text = scan(log_bundle.build(tmp_path), "--no-excerpts")
    assert all("excerpt" not in f for v in data["logs"].values() for f in v["findings"])
    assert "Connection refused" in text  # patterns remain


def test_log_option_limits_the_run_and_top_limits_findings(tmp_path):
    data, _ = scan(log_bundle.build(tmp_path), "--log", "nginx", "--top", "1")
    assert list(data["logs"]) == ["nginx"] and len(data["logs"]["nginx"]["findings"]) == 1
    assert data["logs"]["nginx"]["findings_not_listed"] >= 1


def test_missing_logs_come_back_absent_with_where_they_were_sought(tmp_path):
    data, _ = scan(log_bundle.build(tmp_path, without=("nginx.log", "stacks.txt", "hs_err_pid4242.log")))
    for name in ("nginx", "stacks", "hs_err"):
        assert data["logs"][name]["present"] is False and data["logs"][name]["searched"]
    assert data["logs"]["backend"]["present"] is True


def test_a_bundle_without_install_ini_is_refused(tmp_path):
    proc = subprocess.run([sys.executable, "-I", str(LOGSCAN), str(tmp_path)], capture_output=True, text=True)
    assert proc.returncode != 0 and "install.ini" in proc.stderr
