"""Bundle-reading knowledge (file layout, safe extraction, log/column quirks) is owned by the
reader (skills/dataiku-diagnosis-reader). The checklist-review skill
holds checklist judgment only, and must point at the reader instead of re-documenting it.

A new "where/how do I read X" fact belongs in the reader's references (upstream, then re-sync), not
in the checklist skill. When this test fails, move the fact to the reader and point to it."""

import pytest

from conftest import REPO_ROOT

REVIEW_DIR = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review"

# Reader-owned layout facts: they must not creep into the checklist skill's own text.
READER_OWNED_TERMS = ["ROTA", "lsblk", "[ERROR]", "defaultK8sClusterId", "hs_err_pid", "datadir_listing.txt",
                      "config_listing.txt", "dip.properties", "detailsReadability", "hdfsInterface",
                      "sanity-check.json", "config/clusters", "general-settings.json", "install.ini",
                      "jekSettings", "localAIServerSettings", "managedNamespace", "kubernetesNamespace",
                      "containerSettings", "deployerClientSettings", "project-deployer", "api-deployer",
                      "dss-version.json", "du -sh", "sessionsMax", "forceSingleSessionPerUser",
                      "disableDataTableLinks", "canObtainAPITicket", "lastRunTimestamp", "agent-hub",
                      "userRules", "groupRules", "useAutoFastPath", "azureDWH",
                      "metastoreCatalogsSettings", "graphicsExportsEnabled", "synchronizeTo",
                      "custom_python", "step_based", "envSelection"]


LOG_REVIEW_DIR = REPO_ROOT / "skills" / "dataiku-diagnosis-log-review"
# The log-review skill may name log ids and say "crash dump"; how a log is laid out stays in the reader's logs.md.
LOG_LAYOUT_TERMS = ["[ERROR]", "[WARN]", "hs_err_pid", "nginx.log", "backend.log", "supervisord.log", "frontend.log.0",
                    "ipython.log", "eventserver.log", "install.log", "dmesg.txt", "stacks.txt", "dku_call_id"]


def _files():
    return [REVIEW_DIR / "SKILL.md", REPO_ROOT / "docs" / "verdict-rules.md", *sorted((REVIEW_DIR / "references").glob("*.md")),
            *sorted((REVIEW_DIR / "scripts").glob("*.py"))]


def _reader_fact_keys():
    """The key names the reader publishes in its `security_settings` fact (facts.py SECURITY_KEYS). A rule must name the keys of
    the fact it reads, so rule modules may use these; every other layout term is still forbidden there."""
    import ast

    tree = ast.parse((REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "facts.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SECURITY_KEYS" for t in node.targets):
            return set(ast.literal_eval(node.value))
    return set()


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_checklist_skill_does_not_document_bundle_layout(path):
    text = path.read_text(encoding="utf-8")
    allowed = _reader_fact_keys() if path.name.startswith("rules_") else set()
    found = [t for t in READER_OWNED_TERMS if t in text and not any(t in key for key in allowed)]
    assert not found, f"{path.name} documents reader-owned layout {found}; put it in the reader (upstream)"


def test_checklist_skill_makes_the_reader_a_prerequisite():
    text = (REVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("load the `dataiku-diagnosis-reader` skill", "orient.sh", "facts.py", "limitations.md"):
        assert phrase in text, f"SKILL.md no longer says {phrase!r}"


def test_the_reader_fact_key_exemption_is_limited_to_rule_modules_and_to_the_published_keys():
    keys = _reader_fact_keys()
    assert {"sessionsMaxTotalTimeMinutes", "forceSingleSessionPerUser"} <= keys
    # SKILL.md and the references stay fully covered, and a layout term outside the fact keys is still caught in a rule module
    assert not any(t in key for t in READER_OWNED_TERMS if t in ("general-settings.json", "install.ini", "lsblk") for key in keys)


def _log_review_files():
    return [LOG_REVIEW_DIR / "SKILL.md", *sorted((LOG_REVIEW_DIR / "references").glob("*.md"))]


@pytest.mark.parametrize("path", _log_review_files(), ids=lambda p: p.name)
def test_log_review_skill_does_not_document_bundle_or_log_layout(path):
    text = path.read_text(encoding="utf-8")
    found = [t for t in READER_OWNED_TERMS + LOG_LAYOUT_TERMS if t in text]
    assert not found, f"{path.name} documents reader-owned layout {found}; put it in the reader (upstream)"


def test_log_review_skill_makes_the_reader_a_prerequisite():
    text = (LOG_REVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("dataiku-diagnosis-reader", "orient.sh", "logscan.py", "facts.py", "limitations.md"):
        assert phrase in text, f"SKILL.md no longer says {phrase!r}"
