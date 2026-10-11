"""Verdict rules for the checks that are always Needs Review (judgment only; see verdicts.py for the contract).

These ask about a live system or a customer practice (groups design, proxy, backups, disaster recovery, a service account, network
connectivity, containerized execution) that a diagnosis bundle can never settle, so the status is fixed. The model still writes
`evidence_found` and `notes`: what the bundle does show, and the `Action:` to confirm the rest (see `references/calibrations.md`).
Each rule's text is the human-readable spec in `docs/verdict-rules.md` (keep the two in step)."""
from __future__ import annotations

from verdicts import rule, verdict

_REASON = "a diagnosis bundle cannot settle this check ({why}); review the observations and confirm with the customer"


def _always_needs_review(why: str):
    def decide(facts):
        return verdict("Needs Review", _REASON.format(why=why))
    return decide


for _id, _title, _why in (
    ("SEC-003", "UIF-Managed CGroup Hierarchies Allowed Directories", "the UIF security configuration lives outside the data directory and is not in a bundle"),
    ("SEC-008", "DSS Groups Security Model Appropriately Defined", "group design intent is not in a bundle"),
    ("SEC-011", "Proxy Configuration Reviewed and Documented", "the proxy and its documentation live outside DSS"),
    ("SCALE-005", "Environment Backup Policy", "the backup policy lives outside DSS"),
    ("SCALE-016", "Disaster Recovery Strategy Discussion", "it is a conversation with the customer"),
):
    rule(_id, _title)(_always_needs_review(_why))
