"""scripts/preflight.sh: host tier from the interpreters it can find (stub pythons, no real install needed)."""
import os
import shutil
import subprocess

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "preflight.sh"

STUB = """#!/bin/bash
# stub interpreter: FAKE_OLD=1 -> reports <3.10; FAKE_MISSING lists modules that fail to import
case "$*" in
  *version_info*) exit "${FAKE_OLD:-0}";;
  --version) echo "Python 3.9.0"; exit 0;;
  *"import "*) m="${2#import }"; [[ " $FAKE_MISSING " == *" $m "* ]] && exit 1; exit 0;;
esac
exit 0
"""


def _run(tmp_path, *, stubs=(), old=False, missing=""):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for tool in ("cut", "date"):
        shutil.copy(shutil.which(tool), bin_ / tool)
    for name in stubs:
        (bin_ / name).write_text(STUB)
        (bin_ / name).chmod(0o755)
    root = tmp_path / "plugin"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts" / "preflight.sh")
    env = {"PATH": str(bin_), "PREFLIGHT_PATH_AS_IS": "1", "HOME": str(tmp_path),
           "FAKE_OLD": "1" if old else "0", "FAKE_MISSING": missing}
    out = subprocess.run(["/bin/bash", str(root / "scripts" / "preflight.sh")], env=env, capture_output=True, text=True).stdout
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def test_no_python_at_all_is_facts_only(tmp_path):
    r = _run(tmp_path)
    assert r["TIER"] == "FACTS_ONLY" and "DATAIKU_PYTHON" in r["fix"]


def test_old_python_without_openpyxl_is_facts_only(tmp_path):
    assert _run(tmp_path, stubs=["python3"], old=True, missing="openpyxl")["TIER"] == "FACTS_ONLY"


def test_old_python_with_openpyxl_is_spreadsheet_only(tmp_path):
    r = _run(tmp_path, stubs=["python3"], old=True)
    assert r["TIER"] == "SPREADSHEET" and "no deck" in r["detail"]


def test_python_310_is_full(tmp_path):
    assert _run(tmp_path, stubs=["python3.12"])["TIER"] == "FULL"
