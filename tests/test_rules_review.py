"""The always-Needs-Review rules (scripts/rules_review.py): fixed status whatever the facts hold."""
import sys

import pytest

from conftest import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts"))
import rules_review  # noqa: E402,F401
import verdicts  # noqa: E402

RULED = ["SEC-003", "SEC-008", "SEC-011", "SCALE-005", "SCALE-016"]


@pytest.mark.parametrize("check_id", RULED)
@pytest.mark.parametrize("doc", [{"facts": {}}, {"facts": {"node": {"value": {"nodetype": "design"}, "source": "t"}}}])
def test_always_needs_review(check_id, doc):
    out = verdicts.compute(doc, [{"id": check_id, "title": verdicts.RULES[check_id][0]}])
    assert [v["status"] for v in out["verdicts"]] == ["Needs Review"] and not out["undecided"]
    assert "\n" not in out["verdicts"][0]["reason"]
