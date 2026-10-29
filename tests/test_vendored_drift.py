"""Vendored copies match their upstream checkouts. Skips when the sibling upstream
repos aren't on disk (e.g. in CI); point at other locations with
DATAIKU_REVIEW_GENERATOR_REPO / DATAIKU_DIAGNOSIS_READER_REPO.

A failure here means an upstream change hasn't been re-synced (see CLAUDE.md's
"Vendored vs. authored-here components"), or something was hand-edited here."""

import filecmp
import os
from pathlib import Path

import pytest

from conftest import REPO_ROOT

PARENT = REPO_ROOT.parent


def _checkout(env_var: str, *names: str) -> Path:
    """The upstream checkout: the env var if set, else the first sibling folder that exists.

    The folder name differs between machines, so several are tried. When none exists the first
    candidate is returned and the skip message lists them all."""
    if os.environ.get(env_var):
        return Path(os.environ[env_var])
    candidates = [PARENT / n for n in names]
    return next((c for c in candidates if c.is_dir()), candidates[0])


_GENERATOR_NAMES = ("Dataiku Review Generator", "dataiku-review-generator")
_READER_NAMES = ("Diagnosis Reader", "dataiku-diagnosis-reader")
REVIEW_GENERATOR = _checkout("DATAIKU_REVIEW_GENERATOR_REPO", *_GENERATOR_NAMES)
DIAGNOSIS_READER = _checkout("DATAIKU_DIAGNOSIS_READER_REPO", *_READER_NAMES)
_TRIED = {
    REVIEW_GENERATOR: f"{', '.join(_GENERATOR_NAMES)} (or set DATAIKU_REVIEW_GENERATOR_REPO)",
    DIAGNOSIS_READER: f"{', '.join(_READER_NAMES)} (or set DATAIKU_DIAGNOSIS_READER_REPO)",
}

IGNORE = {".DS_Store", "__pycache__", ".pytest_cache", "node_modules", "dist", ".venv", "resources", "output"}

# (upstream repo, upstream path, path in this repo)
VENDORED = [
    (REVIEW_GENERATOR, "scripts", "mcp-server-review-generator/scripts"),
    (REVIEW_GENERATOR, "config", "mcp-server-review-generator/config"),
    (REVIEW_GENERATOR, "tests", "mcp-server-review-generator/tests"),
    (REVIEW_GENERATOR, "VERSION", "mcp-server-review-generator/VERSION"),
    (REVIEW_GENERATOR, "CHANGELOG.md", "mcp-server-review-generator/CHANGELOG.md"),
    (REVIEW_GENERATOR, "requirements.txt", "mcp-server-review-generator/requirements.txt"),
    (REVIEW_GENERATOR, "requirements-dev.txt", "mcp-server-review-generator/requirements-dev.txt"),
    (REVIEW_GENERATOR, "pytest.ini", "mcp-server-review-generator/pytest.ini"),
    (DIAGNOSIS_READER, "dataiku-diagnosis-reader", "skills/dataiku-diagnosis-reader"),
]


def _diff(a: Path, b: Path, rel: str = "") -> list[str]:
    cmp = filecmp.dircmp(a, b, ignore=list(IGNORE))
    out = [f"only upstream: {rel}{n}" for n in cmp.left_only]
    out += [f"only here: {rel}{n}" for n in cmp.right_only]
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    out += [f"differs: {rel}{n}" for n in mismatch + errors]
    for sub in cmp.common_dirs:
        out += _diff(a / sub, b / sub, f"{rel}{sub}/")
    return out


@pytest.mark.parametrize("upstream,src,dest", VENDORED, ids=[d for _, _, d in VENDORED])
def test_vendored_copy_matches_upstream(upstream, src, dest):
    if not upstream.is_dir():
        pytest.skip(f"upstream checkout not found; looked for a sibling of {PARENT.name}/ named {_TRIED[upstream]}")
    a, b = upstream / src, REPO_ROOT / dest
    assert a.exists(), f"{a} is missing upstream"
    if a.is_file():
        assert filecmp.cmp(a, b, shallow=False), f"{dest} differs from {a}"
    else:
        assert _diff(a, b) == []
