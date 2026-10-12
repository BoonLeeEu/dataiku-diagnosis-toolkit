"""Optional narrative.json for the v2 deck: the human-judgment text (verdict,
takeaways, risk slides, roadmap...) that rules can't derive. It is an *input*,
so the same inputs always give the same deck, and it can never add findings:
every cited ID must exist and its status must support the claim, and every
figure on a risk tile must appear in the cited row's own notes/evidence.

Any missing key falls back to rule-derived content in build_deck_v2.py.
"""

import copy
import hashlib
import json
import re
from pathlib import Path

from deck_analysis import ID_RE, NA, NUMBER_RE, Analysis

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
EFFORTS = {"S", "M", "L"}
TONES = {"good", "risk", "win"}
STATES = {"ok", "watch", "neutral"}


class NarrativeError(ValueError):
    """The narrative file is malformed or contradicts the checklist."""


# Expected JSON shapes, checked before any content rule so a wrong type is reported
# with its path instead of surfacing as a bare TypeError inside a slide builder.
# STR = string, NUM = string or number, IDS = string or list of strings, a dict = an
# object, a one-element list = a list of that. Absent keys are fine (they fall back).
STR, NUM, IDS = "str", "num", "ids"
_ROW_SPEC = {"id": STR, "setting": STR, "from": STR, "to": STR, "confirm": STR}
SHAPE = {
    "checklist_sha256": STR, "verdict_title": STR, "highlights": STR, "snapshot_title": STR, "owners_title": STR,
    "takeaways": [{"heading": STR, "body": STR, "tone": STR}],
    "snapshot": [{"label": STR, "value": STR, "note": STR, "state": STR}],
    "risk1": {"title": STR, "risk": STR, "caveat": STR, "linked_label": STR,
              "tiles": [{"number": NUM, "label": STR, "id": STR, "note": STR}],
              "fix": [{"text": STR, "id": IDS}]},
    "risk2": {"title": STR, "positives": STR,
              "table": [{"id": STR, "setting": STR, "today": STR, "target": STR}]},
    "risk3": {"title": STR, "cards": [{"heading": STR, "ids": IDS, "found": STR, "todo": STR}]},
    "quick_wins": {"title": STR, "rows": [_ROW_SPEC]},
    "owners": {"groups": [{"owner": STR, "asks": [{"id": STR, "ask": STR}]}], "notes": {"*": STR}},
    "roadmap": {"title": STR, "footnote": STR,
                **{col: [{"effort": STR, "action": STR, "ids": IDS}] for col in ("now", "next", "plan")}},
    "na_groups": [{"heading": STR, "note": STR, "ids": IDS}],
    "caveats": IDS,
}
# Fields whose value must come from a fixed set. Shown to the model in scaffold()'s shape so it need not
# discover them from a rejection; validation itself still uses the plain SHAPE above.
_ENUM_FIELDS = {("takeaways", "tone"): TONES, ("snapshot", "state"): STATES, ("roadmap", "effort"): EFFORTS}
MAX_SNAPSHOT_CARDS = 8
_TYPE_NAMES = {dict: "an object", list: "a list", str: "a string", int: "a number", float: "a number",
               bool: "true/false", type(None): "null"}


def documented_shape() -> dict:
    """SHAPE with each enumerated field spelled out, e.g. "state": "str: one of neutral, ok, watch"."""
    def note(values):
        return f"{STR}: one of {', '.join(sorted(values))}"

    doc = copy.deepcopy(SHAPE)
    for tone_parent, field in (("takeaways", "tone"), ("snapshot", "state")):
        doc[tone_parent][0][field] = note(_ENUM_FIELDS[(tone_parent, field)])
    for col in ("now", "next", "plan"):
        doc["roadmap"][col][0]["effort"] = note(EFFORTS)
    return doc


def _shape_problems(value, spec, path, out):
    got = _TYPE_NAMES.get(type(value), type(value).__name__)
    if spec == STR:
        if not isinstance(value, str):
            hint = " (join the items into one string)" if isinstance(value, list) else ""
            out.append(f"{path}: expected a string, got {got}{hint}")
    elif spec == NUM:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            out.append(f"{path}: expected a string or number, got {got}")
    elif spec == IDS:
        if not (isinstance(value, str) or (isinstance(value, list) and all(isinstance(v, str) for v in value))):
            out.append(f"{path}: expected an ID string or a list of ID strings, got {got}")
    elif isinstance(spec, list):
        if not isinstance(value, list):
            out.append(f"{path}: expected a list, got {got}")
            return
        for i, item in enumerate(value, start=1):
            _shape_problems(item, spec[0], f"{path}[{i}]", out)
    else:
        if not isinstance(value, dict):
            out.append(f"{path}: expected an object, got {got}")
            return
        if "*" in spec:
            for k, v in value.items():
                _shape_problems(v, spec["*"], f"{path}.{k}", out)
            return
        for k, sub in spec.items():
            if k in value:
                _shape_problems(value[k], sub, f"{path}.{k}" if path else k, out)


def check_shape(narr: dict):
    """Raise one NarrativeError listing every wrongly-typed field by path."""
    problems = []
    _shape_problems(narr, SHAPE, "", problems)
    if problems:
        raise NarrativeError("Narrative has fields of the wrong type:\n  - " + "\n  - ".join(problems))


def default_path(checklist_path) -> Path:
    """Where a build looks when no narrative is given: beside the checklist,
    named <checklist_stem>_narrative.json."""
    p = Path(checklist_path)
    return p.with_name(f"{p.stem}_narrative.json")


def staleness_warnings(narr: dict, checklist_sha256: str) -> list:
    """The narrative may record the checklist's sha256 (`checklist_sha256`). If the
    checklist changed since, the prose may be stale: warn, don't fail."""
    recorded = narr.get("checklist_sha256")
    if recorded and recorded.lower() != checklist_sha256.lower():
        return ["The narrative was written for a different version of this checklist (checklist_sha256 "
                "differs); re-read it and update the prose before sending the deck."]
    return []


def load(path) -> dict:
    p = Path(path)
    if not p.exists():
        raise NarrativeError(f"Narrative file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NarrativeError(f"Narrative file {p} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise NarrativeError("Narrative file must contain a JSON object at the top level.")
    return data


def _ids(value, where):
    if isinstance(value, str):
        value = ID_RE.findall(value)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise NarrativeError(f"{where}: ids must be a list of strings.")
    return value


def _traces(num, text):
    """True if a figure appears in the text, as digits or spelled out (four = 4)."""
    low = (text or "").lower()
    if num.lower() in low or _numbers(num) <= _numbers(text):
        return True
    return num.isdigit() and int(num) < len(WORDS) and re.search(rf"\b{WORDS[int(num)]}\b", low) is not None


def _numbers(text):
    return {n.strip(".,") for n in NUMBER_RE.findall(text or "")}


def validate(narr: dict, a: Analysis):
    """Raise NarrativeError on contradictions; return a list of soft warnings."""
    check_shape(narr)
    warnings = []
    caveats = set(_ids(narr.get("caveats", []), "caveats"))
    for cid in caveats:
        if cid not in a.rows or a.rows[cid].status != "Pass":
            raise NarrativeError(f"caveats: {cid} must be a Pass item (a 'Pass, with caveat').")

    def check_cited(cid, where, allowed=("Fail", "Partial", "Needs Review")):
        row = a.rows.get(cid)
        if row is None and isinstance(cid, str) and re.search(r"[\s,/;&]", cid.strip()):
            raise NarrativeError(f"{where}: {cid!r} groups several ids; give one checklist id per entry.")
        if row is None:
            raise NarrativeError(f"{where}: {cid} is not in any checklist section sheet.")
        if row.status in allowed or (row.status == "Pass" and cid in caveats):
            return row
        raise NarrativeError(
            f"{where}: {cid} has status {row.status!r}, which doesn't support citing it as a problem "
            f"(allowed: {', '.join(allowed)}; list a Pass item under 'caveats' if it is a Pass with a known issue)."
        )

    r1 = narr.get("risk1") or {}
    for i, t in enumerate(r1.get("tiles", []), start=1):
        cid = t.get("id")
        row = check_cited(cid, f"risk1.tiles[{i}]") if cid else None
        num = str(t.get("number", ""))
        if len(num) > MAX_TILE_NUMBER:
            raise NarrativeError(
                f"risk1.tiles[{i}]: figure {num!r} is longer than {MAX_TILE_NUMBER} characters and won't fit its "
                f"tile; use a smaller figure from the row, or the figure that fits (e.g. a count, not a log total).")
        if row and not _traces(num, row.raw_text):
            raise NarrativeError(
                f"risk1.tiles[{i}]: figure {num!r} does not appear in {cid}'s notes or evidence "
                f"(figures on main slides must trace to a checklist cell)."
            )
    for i, s in enumerate(r1.get("fix", []), start=1):
        for cid in _ids(s.get("id", []), f"risk1.fix[{i}]"):
            check_cited(cid, f"risk1.fix[{i}]")
    for i, e in enumerate((narr.get("risk2") or {}).get("table", []), start=1):
        check_cited(e.get("id"), f"risk2.table[{i}]", ("Fail", "Partial"))
    for i, c in enumerate((narr.get("risk3") or {}).get("cards", []), start=1):
        for cid in _ids(c.get("ids", []), f"risk3.cards[{i}]"):
            check_cited(cid, f"risk3.cards[{i}]")
    for i, q in enumerate((narr.get("quick_wins") or {}).get("rows", []), start=1):
        check_cited(q.get("id"), f"quick_wins.rows[{i}]", ("Fail",))

    groups = (narr.get("owners") or {}).get("groups")
    if groups is not None:
        seen = []
        for g in groups:
            for ask in g.get("asks", []):
                row = check_cited(ask.get("id"), f"owners[{g.get('owner')}]", ("Needs Review",))
                seen.append(row.id)
        for g in groups:
            if len(g.get("asks", [])) > MAX_OWNER_ASKS:
                raise NarrativeError(
                    f"owners[{g.get('owner')}]: {len(g['asks'])} asks don't fit one card (max {MAX_OWNER_ASKS}); "
                    f"move some to another owner.")
        nr = {r.id for r in a.by_status("Needs Review")}
        if len(seen) != len(set(seen)) or set(seen) != nr:
            missing, extra = sorted(nr - set(seen)), sorted(set(seen) - nr)
            raise NarrativeError(
                f"owners: grouped items ({len(seen)}) must equal the Needs Review total ({len(nr)}), each once. "
                f"Missing: {missing}; unexpected/duplicate: {extra}."
            )

    road = narr.get("roadmap") or {}
    for col in ("now", "next", "plan"):
        for i, e in enumerate(road.get(col, []), start=1):
            if str(e.get("effort", "")).upper() not in EFFORTS:
                raise NarrativeError(f"roadmap.{col}[{i}]: effort must be S, M or L.")
            for cid in _ids(e.get("ids", []), f"roadmap.{col}[{i}]"):
                check_cited(cid, f"roadmap.{col}[{i}]")

    na_groups = narr.get("na_groups")
    if na_groups is not None:
        seen = [cid for g in na_groups for cid in _ids(g.get("ids", []), "na_groups")]
        na_ids = {r.id for r in a.by_status(NA)}
        if len(seen) != len(set(seen)) or set(seen) != na_ids:
            raise NarrativeError(
                f"na_groups: must list every Not Applicable item exactly once "
                f"(missing {sorted(na_ids - set(seen))}, unexpected {sorted(set(seen) - na_ids)})."
            )

    for i, t in enumerate(narr.get("takeaways", [])):
        if t.get("tone", "good") not in TONES:
            raise NarrativeError(f"takeaways[{i + 1}].tone must be one of {sorted(TONES)}.")
    if len(narr.get("takeaways", [])) not in (0, 3):
        raise NarrativeError("takeaways: provide exactly 3 (sound / at risk / quick wins) or none.")
    for i, c in enumerate(narr.get("snapshot", []), start=1):
        if c.get("state", "neutral") not in STATES:
            raise NarrativeError(f"snapshot[{i}].state must be one of {sorted(STATES)}.")
    if len(narr.get("snapshot", [])) > MAX_SNAPSHOT_CARDS:
        raise NarrativeError(f"snapshot: at most {MAX_SNAPSHOT_CARDS} cards.")

    # soft check: numbers in free text should exist somewhere in the checklist
    known = _numbers(" ".join(r.raw_text + r.title for r in a.rows.values()))
    known |= {str(v) for v in (*a.counts.values(), a.total, a.applicable)}
    for key in ("verdict_title", "highlights"):
        for n in _numbers(narr.get(key, "")) - known:
            warnings.append(f"narrative {key}: figure {n!r} isn't found in any checklist cell; check it.")
    for i, t in enumerate(narr.get("takeaways", []), start=1):
        for n in _numbers(t.get("body", "")) - known:
            warnings.append(f"narrative takeaways[{i}]: figure {n!r} isn't found in any checklist cell; check it.")
    return warnings


MISSING_WARNING = (
    "No narrative was found for this deck, so its verdict, takeaways, risks, roadmap and owner text are generic "
    "text derived from checklist cells. An LLM-driven run must draft <checklist_stem>_narrative.json from this "
    "checklist (see analyze_checklist) and rebuild; only a plain script run may ship without one."
)

MAX_TILE_NUMBER = 8   # characters; build_deck_v2 shrinks the figure to fit, down to 14pt
MAX_OWNER_ASKS = 14   # rows one owner card can hold

RULES = [
    "Write from this checklist's rows only; never reuse another customer's text.",
    "takeaways: exactly 3 (tones good, risk, win), or omit the key.",
    "owners.groups must cover every Needs Review id exactly once (needs_review below).",
    "na_groups must cover every Not Applicable id exactly once (not_applicable below).",
    "quick_wins rows must be Fail items; risk2.table Fail or Partial; other citations Fail, Partial or Needs Review.",
    "A Pass item may be cited only if listed under caveats.",
    "owners asks: one checklist id per ask (no 'A-1 / A-2'); at most 14 asks per owner.",
    "risk1 tile numbers: at most 8 characters.",
    "Every figure on a risk1 tile must appear in the cited row's notes or evidence_found.",
    "Text fields (positives, action, body, ...) are single strings, not lists; only ids/ids-like fields take lists.",
    "roadmap effort is S, M or L. snapshot has at most 8 cards, each state ok, watch or neutral (a status dot "
    "colour, not good/warn/risk). Record checklist_sha256 (below) once the checklist is final.",
]


def scaffold(a: Analysis, checklist_path) -> dict:
    """Facts a narrative must cite, derived from checklist cells only. Feeds the
    analyze_checklist tool so a draft satisfies validate() first time."""
    path = Path(checklist_path)
    by_status = {}
    for r in a.rows.values():
        by_status.setdefault(r.status, []).append(r.id)

    def brief(r):
        return {"id": r.id, "title": r.title, "priority": r.priority, "section": r.section,
                "status": r.status, "headline": r.headline, "action": r.action}

    return {
        "checklist_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "narrative_path": str(default_path(path)),
        "counts": dict(a.counts), "total": a.total, "applicable": a.applicable,
        "sections": {disp: a.section_counts(disp) for disp, _ in a.section_order},
        "ids_by_status": by_status,
        "root_cause_groups": [list(g) for g in a.root_causes],
        "quick_win_candidates": [{"id": q.id, "setting": q.setting, "from": q.from_, "to": q.to, "confirm": q.confirm}
                                 for q in a.quick_wins],
        "remaining_fails": list(a.remaining_fails),
        "needs_review": [dict(brief(r), suggested_owner=next((o for o, ids in a.owners if r.id in ids), "Other"))
                         for r in a.by_status("Needs Review")],
        "not_applicable": [{"id": r.id, "title": r.title, "section": r.section, "headline": r.headline}
                           for r in a.by_status(NA)],
        "open_items": [brief(r) for r in a.rows.values() if r.status in ("Fail", "Partial")],
        "rules": RULES,
        "shape": documented_shape(),
        "warnings": list(a.warnings),
    }
