"""Shared paths and config loading for the Dataiku Review Generator scripts."""

import copy
import functools
import re
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = REPO_ROOT / "resources"
CONFIG_DIR = REPO_ROOT / "config"
OUTPUT_DIR = REPO_ROOT / "output"

BRANDING_TEMPLATE = RESOURCES_DIR / "Dataiku Branding Template 2026.pptx"

# Fallbacks for when config/deck_layout.yaml omits the key (it normally sets both).
DEFAULT_BASE_DECK = "resources/Dataiku Branding Template 2026.pptx"  # relative to REPO_ROOT
BASE_DECK_ENV = "DATAIKU_BRANDING_TEMPLATE"  # optional absolute path to the template, used when base_deck_path is not given
DEFAULT_ROWS_PER_SLIDE = 4

_LEADING_NUMBER_RE = re.compile(r"^\s*\d+\s*[.)]\s*")


def strip_leading_number(value) -> str:
    """Drop a source-written list numeral ("1. Fix ...", "2) Fix ...") from the front of a
    recommendation; the deck and Summary layouts add their own numbering."""
    return _LEADING_NUMBER_RE.sub("", value or "")

# Single source of truth for this tool's own version (SemVer), read from the
# repo-root VERSION file so every script gets it via `common.VERSION` -- see
# CHANGELOG.md for what changed at each version and CLAUDE.md's "Versioning"
# section for the bump procedure.
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


@functools.lru_cache(maxsize=None)
def _load_config_cached(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(name: str) -> dict:
    """Load a YAML config file from config/ by filename, e.g. 'deck_layout.yaml'.

    Parsed once per process; each caller gets its own copy so edits don't leak."""
    return copy.deepcopy(_load_config_cached(name))


def default_output_path(checklist_path: Path, customer: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", customer).strip("_") or "deck"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", checklist_path.stem)
    date_suffix = m.group(1) if m else datetime.now().strftime("%Y-%m-%d")
    return OUTPUT_DIR / f"{slug}_Platform_Review_{date_suffix}.pptx"
