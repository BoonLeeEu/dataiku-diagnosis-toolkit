"""Write a log-review workbook: an Overview sheet plus one sheet per scanned log.

The caller (a reviewer working from a diagnosis bundle's logs) supplies per-log findings: the grouped error/warning
patterns with count, window and a masked excerpt, and its judgment on each: root cause, confidence, what to check next
and where, and mitigation steps. Everything mechanical is computed here: sheet names, the numbered step lists, the
Overview tables and the hyperlinks from each Overview row to its row on the log's sheet.

Overview: metadata, one row per log (status, totals, window), then one row per finding (severity, pattern, confidence,
likely root cause, link). A log the bundle lacks gets an Overview row and no sheet; a log with no findings gets a sheet
that says so, so absence is visible.

Self-contained: depends only on openpyxl, so it can be lifted out of this repo unchanged.
"""

import os
import re
import textwrap
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.hyperlink import Hyperlink

OVERVIEW = "Overview"
LEVELS = ("FATAL", "ERROR", "WARN")
LEVEL_RANK = {lvl: i for i, lvl in enumerate(LEVELS)}
CONFIDENCES = ("Confirmed", "Likely", "Unknown")
SHEET_NAME_MAX = 31
FORBIDDEN_IN_SHEET_NAME = re.compile(r"[\[\]:*?/\\]")

TITLE_FONT = Font(bold=True, size=14)
LABEL_FONT = Font(bold=True, size=11)
BLOCK_FONT = Font(bold=True, size=12)
BLOCK_FILL = PatternFill("solid", fgColor="FFD9E2F3")
TABLE_HEADER_FONT = Font(bold=True, size=11)
TABLE_HEADER_FILL = PatternFill("solid", fgColor="FFF2F2F2")
LINK_FONT = Font(color="FF0563C1", underline="single")
LEVEL_FILLS = {"FATAL": "FFFFC7CE", "ERROR": "FFFCE4D6", "WARN": "FFFFEB9C"}
CONFIDENCE_FILLS = {"Confirmed": "FFC6EFCE", "Likely": "FFFFEB9C", "Unknown": "FFBDD7EE"}
WRAP = Alignment(wrap_text=True, vertical="top")
LINE_HEIGHT = 15  # points per wrapped line at the default 11pt font
MAX_ROW_LINES = 40  # Excel caps a row at 409pt

LOG_COLUMNS = [  # (header, width)
    ("ID", 14), ("Level", 9), ("Pattern", 48), ("Count", 9), ("First seen", 20), ("Last seen", 20),
    ("Where first seen", 26), ("Masked excerpt", 70), ("Root cause", 50), ("Confidence", 13),
    ("Check next, and where", 50), ("Mitigation steps", 60), ("Notes", 36),
]
OVERVIEW_LOG_COLUMNS = [("Log", 24), ("Sheet", 24), ("Scan result", 16), ("Fatal", 9), ("Errors", 9), ("Warnings", 10),
                        ("Window", 44), ("Note", 60)]
OVERVIEW_FINDING_COLUMNS = [("Log", 24), ("Finding", 14), ("Level", 9), ("Pattern", 48), ("Count", 9),
                            ("Confidence", 13), ("Likely root cause", 60), ("Next step", 60), ("Details", 16)]

# Text that must not reach the workbook: the scanner masks these, so a hit means a finding was not masked.
LEAKS = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "an email address"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "an IPv4 address"),
    (re.compile(r"e:AES:[A-Za-z0-9+/=:_-]+"), "an encrypted secret"),
    (re.compile(r"(?i)\b(?:Bearer|Basic)\s+(?!<secret>)[A-Za-z0-9._~+/=-]{8,}"), "a bearer/basic credential"),
    (re.compile(r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key)[\"']?\s*[=:]\s*[\"']?(?!<secret>)[^\s\"',;&}']+"),
     "a credential value"),
    (re.compile(r"(?i)\bLicense-(?!<licence>)\S+"), "a licence file name"),
]


class LogWorkbookInputError(ValueError):
    """The caller's input can't produce a valid workbook (the message says how to fix it)."""


def _wrapped_lines(text, width) -> int:
    lines = 0
    for part in str(text).split("\n"):
        lines += max(1, len(textwrap.wrap(part, width=max(int(width) - 1, 1), break_long_words=True)))
    return lines


def _numbered(steps) -> str:
    """'1. step' lines; any numbering the caller already put on a step is replaced."""
    cleaned = [re.sub(r"^\s*(?:step\s*)?\d+\s*[.)]\s*", "", str(s).strip(), flags=re.I) for s in steps or []]
    return "\n".join(f"{i}. {s}" for i, s in enumerate([c for c in cleaned if c], 1))


def _bullets(items) -> str:
    cleaned = [str(i).strip() for i in items or [] if str(i).strip()]
    return cleaned[0] if len(cleaned) == 1 else "\n".join(f"- {c}" for c in cleaned)


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _sheet_names(logs) -> dict[str, str]:
    """Log id -> a unique, Excel-legal tab name (<= 31 chars) for every log that gets a sheet."""
    used = {OVERVIEW.lower()}
    names = {}
    for log in logs:
        if not log["present"]:
            continue
        base = FORBIDDEN_IN_SHEET_NAME.sub("-", log["label"]).strip("' ")[:SHEET_NAME_MAX] or log["id"]
        name, n = base, 2
        while name.lower() in used:
            suffix = f" ({n})"
            name, n = base[:SHEET_NAME_MAX - len(suffix)] + suffix, n + 1
        used.add(name.lower())
        names[log["id"]] = name
    return names


def _validate(bundle, reviewer, logs) -> list[dict]:
    problems = []
    if not _text(bundle):
        problems.append("bundle is empty.")
    if not _text(reviewer):
        problems.append("reviewer is empty.")
    if not isinstance(logs, list) or not logs:
        raise LogWorkbookInputError("logs is empty: pass one entry per scanned log.")
    seen_logs, norm = set(), []
    for i, raw in enumerate(logs):
        where = f"logs[{i}]"
        if not isinstance(raw, dict):
            problems.append(f"{where} is not an object.")
            continue
        log_id = _text(raw.get("id"))
        if not log_id:
            problems.append(f"{where} has no id.")
            continue
        where = f"log {log_id!r}"
        if log_id in seen_logs:
            problems.append(f"{where} appears twice.")
        seen_logs.add(log_id)
        present = raw.get("present", True) is not False
        log = {"id": log_id, "label": _text(raw.get("label")) or log_id, "present": present,
               "note": _text(raw.get("note")), "files": raw.get("files") or [], "totals": raw.get("totals"),
               "searched": raw.get("searched") or [], "findings": []}
        findings = raw.get("findings") or []
        if not present and findings:
            problems.append(f"{where} is marked absent but has findings.")
        seen_findings = set()
        for j, f in enumerate(findings):
            fid = _text(f.get("id")) if isinstance(f, dict) else ""
            fwhere = f"{where} finding {fid or j}"
            if not isinstance(f, dict) or not fid:
                problems.append(f"{where} finding {j} has no id.")
                continue
            if fid in seen_findings:
                problems.append(f"{fwhere} appears twice.")
            seen_findings.add(fid)
            level, conf = _text(f.get("level")).upper(), _text(f.get("confidence"))
            count = f.get("count")
            if level not in LEVELS:
                problems.append(f"{fwhere}: level {f.get('level')!r} is not one of {LEVELS}.")
            if not _text(f.get("pattern")):
                problems.append(f"{fwhere}: pattern is empty.")
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                problems.append(f"{fwhere}: count must be a whole number >= 1.")
            if conf not in CONFIDENCES:
                problems.append(f"{fwhere}: confidence {f.get('confidence')!r} is not one of {CONFIDENCES}.")
            steps = [s for s in (f.get("mitigation") or []) if _text(s)]
            checks = [s for s in (f.get("check_next") or []) if _text(s)]
            if conf in ("Confirmed", "Likely"):
                if not _text(f.get("root_cause")):
                    problems.append(f"{fwhere}: {conf} needs a root_cause.")
                if not steps:
                    problems.append(f"{fwhere}: {conf} needs mitigation steps.")
            if conf == "Unknown" and not checks:
                problems.append(f"{fwhere}: Unknown needs check_next (what to look at, and where).")
            blob = "\n".join([_text(f.get("pattern")), *map(_text, f.get("excerpt") or []), _text(f.get("root_cause")),
                              *map(_text, steps), *map(_text, checks), _text(f.get("notes"))])
            for rx, what in LEAKS:
                if rx.search(blob):
                    problems.append(f"{fwhere}: contains {what}; mask it before writing.")
            log["findings"].append({
                "id": fid, "level": level, "pattern": _text(f.get("pattern")), "count": count,
                "first": _text(f.get("first")), "last": _text(f.get("last")),
                "where": _text(f.get("first_seen_at")), "excerpt": [_text(x) for x in f.get("excerpt") or []],
                "root_cause": _text(f.get("root_cause")), "confidence": conf, "check_next": checks, "mitigation": steps,
                "notes": _text(f.get("notes"))})
        log["findings"].sort(key=lambda f: (LEVEL_RANK.get(f["level"], 9), -(f["count"] or 0), f["id"]))
        norm.append(log)
    names = _sheet_names([l for l in norm if l["present"]])
    if problems:
        raise LogWorkbookInputError("Cannot write the workbook:\n- " + "\n- ".join(problems))
    for log in norm:
        log["sheet"] = names.get(log["id"], "")
    return norm


def _window(log) -> str:
    firsts = [f.get("first") for f in log["files"] if f.get("first") not in (None, "", "ABSENT")]
    lasts = [f.get("last") for f in log["files"] if f.get("last") not in (None, "", "ABSENT")]
    if firsts and lasts:
        return f"{min(firsts)} to {max(lasts)}"
    stamps = [f["first"] for f in log["findings"] if f["first"]] + [f["last"] for f in log["findings"] if f["last"]]
    return f"{min(stamps)} to {max(stamps)}" if stamps else ""


def _totals(log) -> dict:
    t = log["totals"]
    if isinstance(t, dict):
        return {lvl: int(t.get(lvl, 0) or 0) for lvl in LEVELS}
    out = {lvl: 0 for lvl in LEVELS}
    for f in log["findings"]:
        out[f["level"]] += f["count"]
    return out


def _put(ws, row, col, value, *, font=None, fill=None, wrap=True):
    cell = ws.cell(row=row, column=col, value=value)
    if font:
        cell.font = font
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    if wrap:
        cell.alignment = WRAP
    return cell


def _link(cell, sheet, row, text):
    cell.value = text
    cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'{sheet}'!A{row}", display=text)
    cell.font = LINK_FONT
    cell.alignment = WRAP


def _table_header(ws, row, columns):
    for col, (header, width) in enumerate(columns, 1):
        _put(ws, row, col, header, font=TABLE_HEADER_FONT, fill="FFF2F2F2")
        letter = openpyxl.utils.get_column_letter(col)
        ws.column_dimensions[letter].width = max(ws.column_dimensions[letter].width or 0, width)


def _fit_row(ws, row, columns):
    lines = 1
    for col, (_, width) in enumerate(columns, 1):
        value = ws.cell(row=row, column=col).value
        if value:
            lines = max(lines, _wrapped_lines(value, width))
    ws.row_dimensions[row].height = min(lines, MAX_ROW_LINES) * LINE_HEIGHT


def _write_log_sheet(ws, log):
    """Write one log's sheet; returns {finding id: its row} for the Overview links."""
    ws.cell(row=1, column=1, value=f"{log['label']}: errors and warnings").font = TITLE_FONT
    back = ws.cell(row=1, column=4)
    back.value = "Back to Overview"
    back.hyperlink = Hyperlink(ref=back.coordinate, location=f"'{OVERVIEW}'!A1", display="Back to Overview")
    back.font = LINK_FONT
    totals = _totals(log)
    summary = (f"Window: {_window(log) or 'not available'}.  Files scanned: {len(log['files']) or 'n/a'}.  "
               f"Fatal {totals['FATAL']}, errors {totals['ERROR']}, warnings {totals['WARN']}.  "
               f"{len(log['findings'])} pattern(s) listed.")
    ws.cell(row=2, column=1, value=summary)
    if log["note"]:
        ws.cell(row=3, column=1, value=log["note"])
    header_row = 5
    _table_header(ws, header_row, LOG_COLUMNS)
    rows = {}
    row = header_row + 1
    if not log["findings"]:
        _put(ws, row, 1, f"No errors or warnings found in {_window(log) or 'the files scanned'}.", wrap=False)
        return rows
    for f in log["findings"]:
        values = [f["id"], f["level"], f["pattern"], f["count"], f["first"], f["last"], f["where"],
                  "\n".join(f["excerpt"]), f["root_cause"], f["confidence"], _bullets(f["check_next"]),
                  _numbered(f["mitigation"]), f["notes"]]
        for col, v in enumerate(values, 1):
            _put(ws, row, col, v)
        ws.cell(row=row, column=2).fill = PatternFill("solid", fgColor=LEVEL_FILLS[f["level"]])
        ws.cell(row=row, column=10).fill = PatternFill("solid", fgColor=CONFIDENCE_FILLS[f["confidence"]])
        _fit_row(ws, row, LOG_COLUMNS)
        rows[f["id"]] = row
        row += 1
    ws.freeze_panes = ws.cell(row=header_row + 1, column=4)
    ws.auto_filter.ref = f"A{header_row}:{openpyxl.utils.get_column_letter(len(LOG_COLUMNS))}{row - 1}"
    return rows


def _write_overview(ws, logs, rows_by_log, meta):
    ws.cell(row=1, column=1, value="Log review: Overview").font = TITLE_FONT
    row = 2
    for label, value in meta:
        ws.cell(row=row, column=1, value=label).font = LABEL_FONT
        ws.cell(row=row, column=2, value=value)
        row += 1
    row += 1
    _put(ws, row, 1, "Logs scanned", font=BLOCK_FONT, fill="FFD9E2F3", wrap=False)
    row += 1
    _table_header(ws, row, OVERVIEW_LOG_COLUMNS)
    row += 1
    for log in logs:
        totals = _totals(log)
        if log["present"]:
            result = "Findings" if log["findings"] else "Clean"
            note = log["note"]
        else:
            result = "Not in bundle"
            note = log["note"] or (f"Looked for: {', '.join(log['searched'])}" if log["searched"] else "")
        values = [log["label"], log["sheet"], result, totals["FATAL"], totals["ERROR"], totals["WARN"], _window(log), note]
        for col, v in enumerate(values, 1):
            _put(ws, row, col, v)
        if log["sheet"]:
            _link(ws.cell(row=row, column=2), log["sheet"], 1, log["sheet"])
        _fit_row(ws, row, OVERVIEW_LOG_COLUMNS)
        row += 1
    row += 1
    _put(ws, row, 1, "Findings", font=BLOCK_FONT, fill="FFD9E2F3", wrap=False)
    row += 1
    _table_header(ws, row, OVERVIEW_FINDING_COLUMNS)
    first_finding_row = row + 1
    row += 1
    flat = [(log, f) for log in logs for f in log["findings"]]
    flat.sort(key=lambda lf: (LEVEL_RANK[lf[1]["level"]], -lf[1]["count"], lf[0]["label"], lf[1]["id"]))
    index = {}
    for log, f in flat:
        next_step = _bullets(f["check_next"]) if f["confidence"] == "Unknown" else _numbered(f["mitigation"][:1])
        values = [log["label"], f["id"], f["level"], f["pattern"], f["count"], f["confidence"],
                  f["root_cause"] or "Not yet determined", next_step, ""]
        for col, v in enumerate(values, 1):
            _put(ws, row, col, v)
        ws.cell(row=row, column=3).fill = PatternFill("solid", fgColor=LEVEL_FILLS[f["level"]])
        ws.cell(row=row, column=6).fill = PatternFill("solid", fgColor=CONFIDENCE_FILLS[f["confidence"]])
        _link(ws.cell(row=row, column=9), log["sheet"], rows_by_log[log["id"]][f["id"]], "Go to details")
        _fit_row(ws, row, OVERVIEW_FINDING_COLUMNS)
        index[(log["id"], f["id"])] = row
        row += 1
    if flat:
        ws.auto_filter.ref = f"A{first_finding_row - 1}:{openpyxl.utils.get_column_letter(len(OVERVIEW_FINDING_COLUMNS))}{row - 1}"
    ws.freeze_panes = "A2"
    return index


def _verify(path: Path, logs, rows_by_log) -> None:
    """Re-open the saved file and check what a reader will rely on: the sheets exist, and every Overview link lands on
    the row that holds the finding it names."""
    wb = openpyxl.load_workbook(path)
    problems = []
    expected = [OVERVIEW] + [l["sheet"] for l in logs if l["present"]]
    if wb.sheetnames != expected:
        problems.append(f"sheets read back as {wb.sheetnames}, expected {expected}.")
    else:
        ov = wb[OVERVIEW]
        wanted = {(l["sheet"], f["id"]) for l in logs for f in l["findings"]}
        linked = set()
        for r in ov.iter_rows():
            for c in r:
                loc = c.hyperlink.location if c.hyperlink is not None else None
                m = re.fullmatch(r"'(.+)'!A(\d+)", loc or "")
                if not m or m.group(1) == OVERVIEW or int(m.group(2)) == 1:
                    continue
                sheet, target = m.group(1), int(m.group(2))
                if sheet not in wb.sheetnames:
                    problems.append(f"link {c.coordinate} points at missing sheet {sheet!r}.")
                    continue
                fid = wb[sheet].cell(row=target, column=1).value
                linked.add((sheet, fid))
                if ov.cell(row=c.row, column=2).value != fid:
                    problems.append(f"link {c.coordinate} names {ov.cell(row=c.row, column=2).value!r} but lands on {fid!r}.")
        if linked != wanted:
            problems.append(f"{len(wanted - linked)} finding(s) have no working Overview link.")
    if problems:
        raise RuntimeError("Log workbook round-trip check failed:\n- " + "\n- ".join(problems))


def write_log_workbook(
    output_path,
    *,
    bundle: str,
    reviewer: str,
    logs: list,
    node_version: str = "",
    diagnosis_generated: str = "",
    today: date | None = None,
) -> dict:
    """Write the workbook at `output_path` (replacing a file already there).

    logs: one entry per log the scan covered, in the order to show them:
        {"id", "label", "present" (false = not in the bundle), "searched", "note", "files": [{"first", "last"}],
         "totals": {"WARN", "ERROR", "FATAL"}, "findings": [{"id", "level", "pattern", "count", "first", "last",
         "first_seen_at", "excerpt": [masked lines], "root_cause", "confidence" (Confirmed | Likely | Unknown),
         "check_next": [what to look at, and where], "mitigation": [steps], "notes"}]}
    Confirmed and Likely findings need a root cause and mitigation steps; Unknown ones need check_next.
    Raises LogWorkbookInputError for bad input (before touching any file) and RuntimeError if the saved file fails the
    round-trip check (the existing file is then left unchanged).
    """
    path = Path(output_path)
    if path.suffix.lower() != ".xlsx":
        raise LogWorkbookInputError(f"output_path must end in .xlsx, got {path.name!r}.")
    norm = _validate(bundle, reviewer, logs)

    wb = openpyxl.Workbook()
    ov = wb.active
    ov.title = OVERVIEW
    rows_by_log = {}
    for log in norm:
        if log["present"]:
            rows_by_log[log["id"]] = _write_log_sheet(wb.create_sheet(log["sheet"]), log)
    meta = [("Bundle:", _text(bundle)), ("Node / Version:", _text(node_version)),
            ("Diagnosis generated:", _text(diagnosis_generated)),
            ("Report generated:", (today or date.today()).isoformat()), ("Reviewer:", _text(reviewer))]
    _write_overview(ov, norm, rows_by_log, meta)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".logs-tmp" + path.suffix)
    wb.save(tmp)
    try:
        _verify(tmp, norm, rows_by_log)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

    findings = [f for l in norm for f in l["findings"]]
    return {
        "output_path": str(path),
        "sheets": [OVERVIEW] + [l["sheet"] for l in norm if l["present"]],
        "logs_with_findings": [l["id"] for l in norm if l["findings"]],
        "logs_clean": [l["id"] for l in norm if l["present"] and not l["findings"]],
        "logs_not_in_bundle": [l["id"] for l in norm if not l["present"]],
        "findings": len(findings),
        "by_level": {lvl: sum(1 for f in findings if f["level"] == lvl) for lvl in LEVELS},
        "by_confidence": {c: sum(1 for f in findings if f["confidence"] == c) for c in CONFIDENCES},
    }
