#!/usr/bin/env python3
"""Errors and warnings of a Dataiku diagnosis bundle's major logs, grouped and masked, as one JSON report.

Usage: logscan.py <bundle_root> [--log ID ...] [--top N] [--no-excerpts] [--since TS] [--until TS]
                  [--around TS [--window 30m]] [--timeline]

Prints `{"bundle_root", "mirror", "logs": {log_id: {...}}}` (`bundle_root` is the folder's name and `mirror` its path
relative to it, never an absolute path). Per log: whether it is present, its `tz` (what its timestamps are relative to),
its files with size and first/last timestamp, WARN/ERROR/FATAL totals, and `findings`: one per normalised message
pattern, each with count, first/last timestamp, where it was first seen (`file:line`, relative to the mirror or bundle
root) and, unless `--no-excerpts`, a short masked excerpt (the line plus a few continuation lines, `Caused by:` lines
kept). Findings that match a known serious signature (`signature`: oom, deadlock, process_crash, disk_full, ...) come
first and are never cut by `--top`; known scanner noise (`noise`) comes last.

`--since/--until` (ISO, e.g. 2026-07-21T08:00 or a date) keep only records in that window; `--around TS --window 30m`
is the same as since/until of TS -/+ window. Logs whose timestamps are not wall-clock (dmesg, stacks, code-env logs)
are not filtered (`time_filter: not_applicable`). `--timeline` adds one merged, time-sorted list of the signature and
FATAL events of every log; timestamps of different logs are naive local times unless an event says otherwise (`tz`).

Logs: backend, frontend, nginx, ipython, eventserver, supervisord, install, install-impersonation, codeenv (code
environment build logs), dmesg, stacks, hs_err. `--log` limits the run to some of them.

It exists so a reviewer groups errors by pattern instead of reading ~100MB files. Each file is streamed once and never
loaded whole. Masking is best effort (emails, IPs, URL hosts, users, project keys, secrets, licence file names): a
person must still look before an excerpt leaves the machine. Compressed rotations (`.gz`, `.zip`) are not read
(`gz_files_skipped`). Read-only; no network calls; Python 3 stdlib only.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

ABSENT = "ABSENT"
RANK = {"FATAL": 3, "ERROR": 2, "WARN": 1}
CANON = {"FATAL": "FATAL", "CRITICAL": "FATAL", "CRIT": "FATAL", "EMERG": "FATAL", "ALERT": "FATAL",
         "ERROR": "ERROR", "WARN": "WARN", "WARNING": "WARN",
         "error": "ERROR", "crit": "ERROR", "alert": "ERROR", "emerg": "FATAL", "warn": "WARN"}
PATTERN_CAP, PATTERN_WIDTH, LINE_WIDTH = 500, 140, 300
CONTINUATION_SCAN, CONTINUATION_KEEP, CAUSE_KEEP = 60, 3, 3
TAIL_BYTES = 256 * 1024
EVENT_CAP, TIMELINE_CAP, PATTERN_EVENTS = 500, 1000, 10  # timeline events kept per log, in all, per pattern

# ---- masking -------------------------------------------------------------------------------------------------------
MASKS = [
    (re.compile(r"(?i)\b(https?|ftp|s3|gs|abfss?|wasbs?|hdfs|jdbc:[a-z0-9]+)://[^/\s\"'`]+"), r"\1://<host>"),
    (re.compile(r"e:AES:[A-Za-z0-9+/=:_-]+"), "<secret>"),
    (re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 <secret>"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|authorization)([\"']?\s*[=:]\s*)[\"']?[^\s\",;&}']+"),
     r"\1\2<secret>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]*)?"), "<jwt>"),
    (re.compile(r"(?i)\b(License-)\S+"), r"\1<licence>"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<email>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<ip>"),
    (re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}\b"), "<ip>"),
    (re.compile(r"(?i)\b(host|server|upstream|referrer|referer|client)(\"?\s*[=:]\s*)\"?[^\s\",;]+"), r"\1\2<host>"),
    (re.compile(r"(?i)\b(user|username|login|owner)=\S+"), r"\1=<user>"),
    (re.compile(r"(?i)\b(user) '[^']*'"), r"\1 '<user>'"),
    (re.compile(r"(/home/)[^/\s]+"), r"\1<user>"),
    (re.compile(r"\b(task_memcg|oom_memcg|cgroup)=\S+"), r"\1=<cgroup>"),
    (re.compile(r"\b(Notebook\s+)\S+/.*?(\.ipynb)"), r"\1<project>/<notebook>\2"),
    (re.compile(r"\b((?i:projectKey|project_key|project))([\"']?\s*[=:]\s*[\"']?|\s+)([A-Z][A-Z0-9_]{2,})\b"),
     r"\1\2<project>"),
    (re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9_]{2,}\.(?=[\w-])"), "<project>."),
    (re.compile(r"(<project>\.)(?:<project>\.)+"), r"\1"),
    (re.compile(r"(?<=<project>\.)[\w-]+(?:\.[\w-]+)*"), "<id>"),
    (re.compile(r"(?<=/)[A-Z][A-Z0-9_]{3,}(?=/)"), "<project>"),
    (re.compile(r"(webappruns/[^/\s]+/)[\w-]+"), r"\1<id>"),
    (re.compile(r"(?<![\w<>])(recipes|datasets|scenarios|web_apps|saved_models|managed_folders|notebooks)/[^/\s\"']+?(\.\w+)\b"),
     r"\1/<name>\2"),
    (re.compile(r"\b(FT-\w+?Instance-)[\w-]+"), r"\1<id>"),
    (re.compile(r"\bCustomCode_[\w-]+"), "CustomCode_<plugin>"),
    (re.compile(r"(/plugins/(?:installed|dev)/)[\w.-]+"), r"\1<plugin>"),
    (re.compile(r"(?<![\w<>.:])/(?:apps|opt|data|srv|mnt|export|Users|var/lib|usr/local)/(?:[\w.-]+/)+"), "/<path>/"),
    (re.compile(r"\b(\w*(?:Id|Key|Name|Ref))=[^\s,;]+"), r"\1=<id>"),
    # NAMES_LIKE_THIS are scenario, dataset and recipe ids; kernel and DSS constants are left alone
    (re.compile(r"\b(?!(?:GFP|CONSTRAINT|DIP|DKU|JAVA|HTTP|SQL|LD)_)[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b"), "<id>"),
]


def mask(text):
    for rx, repl in MASKS:
        text = rx.sub(repl, text)
    return text


def clip(text, width=LINE_WIDTH):
    text = text.rstrip("\r\n")
    return text if len(text) <= width else text[:width - 1] + "…"


CLAUSE = re.compile(r": | \{| \[")
EXC_CLASS = re.compile(r"(?:[\w$]+\.)*\w*(?:Exception|Error)")
THREAD = re.compile(r"^(\[\d{4}/[^\]]*\] )\[([^\]]*)\]")


def first_clause_of(msg):
    """The message up to its first ": ", ` {` or ` [`; a bare exception class keeps its message too ("IOException: disk")."""
    m = CLAUSE.search(msg)
    if not m:
        return msg
    if EXC_CLASS.fullmatch(msg[:m.start()]) and m.group().startswith(": "):
        m2 = CLAUSE.search(msg, m.end())
        return msg[:m2.start()] if m2 else msg
    return msg[:m.start()]


def mask_line(line):
    """`mask` for a whole log line: the thread name keeps its alphabetic prefix only (`jek-2` -> `jek`)."""
    m = THREAD.match(line)
    if m:
        name = re.match(r"[A-Za-z]+(?:-[A-Za-z]+)*", m.group(2))
        line = m.group(1) + "[" + (name.group(0) if name else "<thread>") + "]" + line[m.end():]
    return mask(line)


def normalise(msg, quotes=True, first_clause=True):
    """A stable key for a message: masked, quoted text and numbers replaced, so repeats of one failure group together."""
    msg = mask(msg.strip())
    if quotes:
        msg = re.sub(r"'[^']*'|\"[^\"]*\"", "'<x>'", msg)
    if first_clause:
        msg = first_clause_of(msg)
    msg = re.sub(r"0x[0-9a-fA-F]+", "0xN", msg)
    return re.sub(r"\d+", "N", msg)[:PATTERN_WIDTH]


# ---- time -----------------------------------------------------------------------------------------------------------
def iso_std(ts):
    """'2026/01/03-01:02:00' or '2026-01-03 01:02:00' -> '2026-01-03T01:02:00'; None when it is not a wall-clock time."""
    m = re.match(r"(\d{4})[/-](\d\d)[/-](\d\d)[-T ](\d\d:\d\d:\d\d)", ts or "")
    return f"{m[1]}-{m[2]}-{m[3]}T{m[4]}" if m else None


def hs_parse(when):
    """hs_err `Time:` ('Fri Dec  5 08:12:11 2025 UTC') -> (ISO time, zone name); (None, None) when it does not parse."""
    parts = (when or "").split()
    try:
        dt = datetime.datetime.strptime(" ".join(parts[:5]), "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None, None
    return dt.strftime("%Y-%m-%dT%H:%M:%S"), (parts[5] if len(parts) > 5 else None)


def parse_when(text, end=False):
    """A user-supplied ISO time or date -> '%Y-%m-%dT%H:%M:%S'; a bare date given as an end bound means the day's end."""
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        sys.exit(f"logscan.py: cannot read '{text}' as an ISO time (e.g. 2026-07-21T08:00 or 2026-07-21)")
    if end and len(text) == 10:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def parse_span(text):
    m = re.fullmatch(r"(\d+)([smhd])", text)
    if not m:
        sys.exit(f"logscan.py: cannot read '{text}' as a span (e.g. 30m, 2h, 1d)")
    return datetime.timedelta(**{{"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}[m.group(2)]: int(m.group(1))})


class Window:
    """The --since/--until bounds, as ISO strings (they compare as text)."""

    def __init__(self, since=None, until=None):
        self.since, self.until = since, until
        self.active = bool(since or until)

    def keep(self, iso):
        return iso is None or ((not self.since or iso >= self.since) and (not self.until or iso <= self.until))

    def outside(self, first_iso, last_iso):
        return bool((self.since and last_iso and last_iso < self.since) or (self.until and first_iso and first_iso > self.until))


WIN = Window()
TIMELINE = False

# ---- signatures and noise ------------------------------------------------------------------------------------------------
# Starter set of failures a support engineer wants first, whatever their count. Matched on the raw line of a pattern's
# first sighting. Verify a new entry against a real bundle before adding it (INTENT principle 2).
SIGNATURES = re.compile("|".join(f"(?P<{name}>{rx})" for name, rx in [
    ("oom", r"OutOfMemoryError|Out of memory|oom-kill|oom_reaper|invoked oom-killer|Killed process|Out of Memory Error"),
    ("deadlock", r"(?i:deadlock)"),
    ("process_crash", r"entered FATAL state|gave up|exited: .*not expected|spawn error|JVM crash|SIGSEGV|SIGBUS"),
    ("disk_full", r"No space left on device|Disk quota exceeded"),
    ("fd_exhaustion", r"Too many open files"),
    ("licence", r"(?i:licen[sc]e[^\n]{0,60}(?:expired|invalid|exceeded|not valid|missing)|(?:expired|invalid)[^\n]{0,30}licen[sc]e)"),
    ("db_connection", r"PSQLException|Hikari\w*[^\n]{0,80}(?:timed out|not available)|too many clients|FATAL: (?:password|sorry)"),
    ("run_as_user", r"configured to run as user"),
]))
SCANNER_NOISE = re.compile(
    r"/\.(?:aws|ada|env|git|ssh|svn|ds_store)\b|wp-(?:admin|login|content|includes)|cgi-bin|\.(?:php|aspx?|jsp)\b|phpmyadmin|"
    r"/etc/passwd|No such file or directory|directory index of|access forbidden by rule|client sent (?:invalid|HTTP)")


def signature(text):
    m = SIGNATURES.search(text)
    return m.lastgroup if m else None


# ---- line parsers: each returns (ts, level, logger, message) for a record that matters, else None ---------------------
BRACKET = re.compile(r"^\[(\d{4}/\d\d/\d\d-\d\d:\d\d:\d\d)(?:\.\d+)?\] \[[^\]]*\] \[([A-Z]+)\] \[([^\]]*)\]\s*"
                     r"(?:\[dku_call_id=\w+\])?\s*(?:-\s*)?(.*)$", re.S)
BRACKET_START = re.compile(r"^\[(\d{4}/\d\d/\d\d-\d\d:\d\d:\d\d)")
PLAIN_LEVEL = re.compile(r"^(ERROR|WARNING|CRITICAL)(?::[\w.]*)?[: ]\s*(.*)$", re.S)
PLAIN_EXC = re.compile(r"^(?:[\w$]+\.)*\w*(?:Exception|Error)\b.*", re.S)  # the "Traceback" header is not an event: its last line is
SUPERVISOR = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ (\w+) (.*)$", re.S)
SUPERVISOR_SERIOUS = re.compile(r"entered FATAL state|gave up|exited: .*not expected|spawn error|can't find command")
NGINX = re.compile(r"^(\d{4})/(\d\d)/(\d\d) (\d\d:\d\d:\d\d) \[(\w+)\] \d+#\d+: (?:\*\d+ )?(.*)$", re.S)
NGINX_PRE = re.compile(r"^nginx: \[(\w+)\] (.*)$", re.S)
DMESG = re.compile(r"^\[\s*([\d.]+)\] (.*)$", re.S)
DMESG_RULES = [(re.compile(r"Out of memory|oom-kill|oom_reaper|Killed process|invoked oom-killer"), "ERROR"),
               (re.compile(r"segfault|general protection|Call Trace|I/O error|EXT4-fs error|XFS .*(?:error|corrupt)|"
                           r"blk_update_request|Buffer I/O error"), "ERROR"),
               (re.compile(r"blocked for more than|hung_task|soft lockup|hard LOCKUP|nf_conntrack: table full|"
                           r"TCP: .*Dropping|Out of socket memory|throttling"), "WARN")]
PIP_RULES = [(re.compile(r"^\s*WARNING: |Retrying"), "WARN"),
             (re.compile(r"^\s*(?:ERROR|error): |No matching distribution|ResolutionImpossible|Failed building wheel|"
                         r"subprocess-exited-with-error|Traceback \(most recent|ModuleNotFoundError|ImportError|"
                         r"Could not (?:find|fetch|install)|Connection (?:refused|timed out)|SSL.*(?:Error|certificate)"), "ERROR")]
ENV_LOG_DIRS = ("code-envs", "acode-envs")


def parse_bracket(line, plain=False):
    m = BRACKET.match(line)
    if m:
        lvl = CANON.get(m.group(2))
        if lvl:
            return m.group(1), lvl, m.group(3), m.group(4)
        if "OutOfMemoryError" in line:
            return m.group(1), "ERROR", m.group(3), m.group(4)
        return None
    if "OutOfMemoryError" in line and BRACKET_START.match(line):
        return BRACKET_START.match(line).group(1), "ERROR", "", line
    if plain:
        p = PLAIN_LEVEL.match(line)
        if p:
            return None, CANON[p.group(1)], "installer", p.group(2)
        if PLAIN_EXC.match(line):
            return None, "ERROR", "installer", line
    return None


def parse_supervisor(line):
    m = SUPERVISOR.match(line)
    if not m:
        return None
    ts, lvl_raw, msg = m.groups()
    lvl = CANON.get(lvl_raw)
    if SUPERVISOR_SERIOUS.search(msg):
        lvl = "ERROR" if lvl in (None, "WARN") else lvl
    return (ts, lvl, "supervisord", msg) if lvl else None


def parse_nginx(line):
    m = NGINX.match(line)
    if m:
        lvl = CANON.get(m.group(5))
        if lvl:
            y, mo, d, hms = m.group(1, 2, 3, 4)
            return f"{y}/{mo}/{d}-{hms}", lvl, "nginx", m.group(6).split(", client:", 1)[0]
        return None
    p = NGINX_PRE.match(line)
    if p and CANON.get(p.group(1)):
        return None, CANON[p.group(1)], "nginx", p.group(2)
    return None


def parse_dmesg(line):
    m = DMESG.match(line)
    if not m:
        return None
    for rx, lvl in DMESG_RULES:
        if rx.search(m.group(2)):
            return m.group(1), lvl, "kernel", m.group(2)
    return None


def parse_pip(line):
    for rx, lvl in PIP_RULES:
        if rx.search(line):
            return None, lvl, "pip", line
    return None


def starts_bracket(line):
    m = BRACKET_START.match(line)
    return m.group(1) if m else None


def starts_supervisor(line):
    m = SUPERVISOR.match(line)
    return m.group(1) if m else None


def starts_nginx(line):
    m = NGINX.match(line)
    return f"{m.group(1)}/{m.group(2)}/{m.group(3)}-{m.group(4)}" if m else None


def starts_dmesg(line):
    m = DMESG.match(line)
    return m.group(1) if m else None


def no_start(line):
    return None


# Each spec: where the files are, how to parse, the cheap byte filters a line must contain to be worth parsing, and
# whether quoted text is a variable (True for DSS logs, False for supervisord where quotes name the process).
BRACKET_PREFILTER = (b"[WARN]", b"[WARNING]", b"[ERROR]", b"[FATAL]", b"OutOfMemoryError")
SPECS = {
    "backend": dict(label="backend.log", base="backend.log", parse=parse_bracket, starts=starts_bracket,
                    prefilter=BRACKET_PREFILTER),
    "frontend": dict(label="frontend.log", base="frontend.log", parse=parse_bracket, starts=starts_bracket,
                     prefilter=BRACKET_PREFILTER),
    "ipython": dict(label="ipython.log", base="ipython.log", parse=parse_bracket, starts=starts_bracket,
                    prefilter=BRACKET_PREFILTER),
    "eventserver": dict(label="eventserver.log", base="eventserver.log", parse=parse_bracket, starts=starts_bracket,
                        prefilter=BRACKET_PREFILTER),
    "supervisord": dict(label="supervisord.log", base="supervisord.log", parse=parse_supervisor,
                        starts=starts_supervisor, quotes=False, clause=False,
                        prefilter=(b" WARN ", b" ERRO", b" CRIT ", b" FATAL ", b"entered FATAL", b"gave up",
                                   b"not expected", b"spawn error")),
    "nginx": dict(label="nginx.log", base="nginx.log", parse=parse_nginx, starts=starts_nginx, clause=False,
                  prefilter=(b"[warn]", b"[error]", b"[crit]", b"[alert]", b"[emerg]")),
    "install": dict(label="install.log", base="install.log", parse=lambda ln: parse_bracket(ln, plain=True),
                    starts=starts_bracket, prefilter=BRACKET_PREFILTER + (b"ERROR", b"WARNING", b"Exception", b"Error")),
    "install-impersonation": dict(label="install-impersonation.log", base="install-impersonation.log",
                                  parse=lambda ln: parse_bracket(ln, plain=True), starts=starts_bracket,
                                  prefilter=BRACKET_PREFILTER + (b"ERROR", b"WARNING", b"Exception", b"Error")),
}
ROTATED = ("backend", "frontend", "ipython", "eventserver", "nginx")
for _spec in SPECS.values():
    _spec.update(iso=iso_std, tz="local")  # wall-clock time of the DSS host, no zone recorded


# ---- aggregation ---------------------------------------------------------------------------------------------------
class Acc:
    """Findings of one log, keyed by (level, pattern). Keeps at most PATTERN_CAP patterns; the rest are only counted.
    `keyfn` turns a raw timestamp into something that orders correctly (ISO text, seconds since boot, ...)."""

    def __init__(self, keyfn=iso_std, tz=None):
        self.entries = {}
        self.overflow = 0
        self.totals = {"WARN": 0, "ERROR": 0, "FATAL": 0}
        self.files = []
        self.keyfn, self.tz = keyfn, tz
        self.events, self.events_dropped, self.events_untimed = [], 0, 0

    def add(self, level, pattern, ts, where, file_key, excerpt, sig=None, iso_ts=None, tz=None):
        self.totals[level] += 1
        key = (level, pattern)
        e = self.entries.get(key)
        if e is None:
            if len(self.entries) >= PATTERN_CAP:
                self.overflow += 1
                return None
            e = self.entries[key] = {"level": level, "pattern": pattern, "count": 0, "first": None, "last": None,
                                     "first_k": None, "last_k": None, "first_seen_at": where, "files": set(),
                                     "excerpt": excerpt, "sig": sig, "events": 0}
        e["count"] += 1
        e["files"].add(file_key)
        if ts:
            k = self.keyfn(ts)
            if k is None:
                e["first"] = e["first"] or ts
                e["last"] = e["last"] or ts
            else:
                if e["first_k"] is None or k < e["first_k"]:
                    e["first_k"], e["first"] = k, ts
                if e["last_k"] is None or k > e["last_k"]:
                    e["last_k"], e["last"] = k, ts
        if TIMELINE and (e["sig"] or level == "FATAL"):
            if not iso_ts:
                self.events_untimed += 1
            elif e["events"] >= PATTERN_EVENTS or len(self.events) >= EVENT_CAP:
                self.events_dropped += 1
            else:
                e["events"] += 1
                self.events.append({"at": iso_ts, "tz": tz or self.tz, "level": level, "signature": e["sig"],
                                    "pattern": pattern, "where": where})
        return e

    def findings(self, log_id, top, with_excerpts):
        def noise(e):
            return e["sig"] is None and bool(SCANNER_NOISE.search(e["pattern"]))

        ordered = sorted(self.entries.values(),
                         key=lambda e: (e["sig"] is None, noise(e), -RANK[e["level"]], -e["count"], e["pattern"]))
        sigs = sum(1 for e in ordered if e["sig"])
        keep = ordered[:max(top, sigs)]  # signature findings are never cut by --top
        out = []
        for i, e in enumerate(keep, 1):
            f = {"id": f"{log_id}-{i:03d}", "key": hashlib.sha1(f"{e['level']}|{e['pattern']}".encode()).hexdigest()[:8],
                 "level": e["level"], "pattern": e["pattern"], "count": e["count"], "first": e["first"] or ABSENT,
                 "last": e["last"] or ABSENT, "first_seen_at": e["first_seen_at"], "files_affected": len(e["files"])}
            if e["sig"]:
                f["signature"] = e["sig"]
            elif noise(e):
                f["noise"] = "scanner-probe"
            if with_excerpts:
                f["excerpt"] = e["excerpt"]
            out.append(f)
        return out, max(0, len(ordered) - len(keep))


def window(path, starts):
    """First and last record timestamp of a file without reading it whole: the head for the first, the tail for the last."""
    first = last = None
    with open(path, "rb") as fh:
        for _, raw in zip(range(5000), fh):
            first = starts(raw.decode("utf-8", "replace"))
            if first:
                break
        size = os.fstat(fh.fileno()).st_size
        fh.seek(max(0, size - TAIL_BYTES))
        for raw in fh.read().splitlines():
            ts = starts(raw.decode("utf-8", "replace"))
            if ts:
                last = ts
    return first or ABSENT, last or ABSENT


def rotation_key(name):
    """Oldest first: a higher rotation number is older, the unnumbered file is the newest."""
    tail = name.rsplit(".", 1)[-1]
    return -int(tail) if tail.isdigit() else 1


PREFILTERS = {}


def prefilter_rx(prefilter):
    """One compiled byte regex for a spec's cheap filters: a single C-level search per line instead of a Python loop."""
    if prefilter not in PREFILTERS:
        PREFILTERS[prefilter] = re.compile(b"|".join(re.escape(p) for p in prefilter))
    return PREFILTERS[prefilter]


def scan_stream(path, rel, spec, acc, with_excerpts):
    parse, starts, iso = spec["parse"], spec["starts"], spec.get("iso")
    rx = prefilter_rx(spec["prefilter"])
    quotes = spec.get("quotes", True)
    counts = {"WARN": 0, "ERROR": 0, "FATAL": 0}
    cap = None  # [entry, scanned, kept, cause_kept] while collecting the continuation of a first occurrence
    last_iso = None  # the last record time seen, which a record without one (installer lines) follows
    with open(path, "rb") as fh:
        for n, raw in enumerate(fh, 1):
            hit = rx.search(raw) is not None
            line = None
            if cap is not None:
                line = raw.decode("utf-8", "replace")
                if starts(line) is None and not (hit and parse(line) is not None) and cap[1] < CONTINUATION_SCAN:
                    cap[1] += 1
                    if not line.strip():
                        continue
                    if line.lstrip().startswith("Caused by:") and cap[3] < CAUSE_KEEP:
                        cap[0]["excerpt"].append(clip(mask(line)))
                        cap[3] += 1
                    elif cap[2] < CONTINUATION_KEEP:
                        cap[0]["excerpt"].append(clip(mask(line)))
                        cap[2] += 1
                    continue
                cap = None
            if not hit:
                continue
            line = line if line is not None else raw.decode("utf-8", "replace")
            ev = parse(line)
            if ev is None:
                continue
            ts, level, logger, msg = ev
            iso_ts = iso(ts) if iso and ts else None
            if iso_ts:
                last_iso = iso_ts
            elif ts is None:
                iso_ts = last_iso
            if WIN.active and iso and not WIN.keep(iso_ts):
                continue
            counts[level] += 1
            pattern = normalise(msg, quotes=quotes, first_clause=spec.get("clause", True))
            pattern = f"[{logger}] {pattern}"[:PATTERN_WIDTH] if logger and logger not in pattern else pattern
            fresh = (level, pattern) not in acc.entries
            e = acc.add(level, pattern, ts, f"{rel}:{n}", rel, [clip(mask_line(line))] if with_excerpts else [],
                        sig=signature(line) if fresh else None, iso_ts=iso_ts, tz=spec.get("tz"))
            if e is not None and fresh and with_excerpts:
                cap = [e, 0, 0, 0]
    return counts


def scan_files(log_id, mirror, with_excerpts):
    spec = SPECS[log_id]
    base = os.path.join(mirror, "run")
    if not os.path.isdir(base):
        return {"present": False, "searched": ["run"]}
    pat = re.compile(re.escape(spec["base"]) + r"(\.\d+)?")
    gz = re.compile(re.escape(spec["base"]) + r".*\.(gz|zip)")
    names = sorted((n for n in os.listdir(base) if pat.fullmatch(n)), key=rotation_key)
    skipped = sorted(n for n in os.listdir(base) if gz.fullmatch(n))
    if not names:
        return {"present": False, "searched": [f"run/{spec['base']}*"]}
    acc = Acc(tz=spec.get("tz"))
    for n in names:
        path = os.path.join(base, n)
        first, last = window(path, spec["starts"])
        entry = {"file": f"run/{n}", "size_bytes": os.path.getsize(path), "first": first, "last": last}
        if WIN.active and WIN.outside(iso_std(first), iso_std(last)):
            acc.files.append({**entry, "WARN": 0, "ERROR": 0, "FATAL": 0, "skipped_outside_window": True})
            continue
        acc.files.append({**entry, **scan_stream(path, f"run/{n}", spec, acc, with_excerpts)})
    return acc, skipped


def scan_codeenv(mirror, with_excerpts):
    logs = []
    for dirpath, dirs, files in os.walk(mirror):
        if dirpath[len(mirror):].count(os.sep) > 5:
            dirs[:] = []
            continue
        if os.path.basename(dirpath) == "logs" and os.path.basename(os.path.dirname(dirpath)) in ENV_LOG_DIRS:
            for sub, _, names in os.walk(dirpath):
                logs.extend(os.path.join(sub, n) for n in names if n.endswith(".log"))
    if not logs:
        return {"present": False, "searched": ["code-envs/logs", "acode-envs/logs"]}
    spec = {"parse": parse_pip, "starts": no_start, "prefilter": (b"ERROR", b"error", b"WARNING", b"Retrying", b"Could not",
                                                                   b"No matching", b"Traceback", b"Error"),
            "clause": False}
    acc = Acc()
    for path in sorted(logs):
        rel = os.path.relpath(path, mirror)
        counts = scan_stream(path, rel, spec, acc, with_excerpts)
        acc.files.append({"file": rel, "size_bytes": os.path.getsize(path), "first": ABSENT, "last": ABSENT, **counts})
    return acc, []


def scan_dmesg(root, with_excerpts):
    path = os.path.join(root, "dmesg.txt")
    if not os.path.isfile(path):
        return {"present": False, "searched": ["dmesg.txt"]}
    spec = {"parse": parse_dmesg, "starts": starts_dmesg, "clause": False,
            "prefilter": (b"Out of memory", b"oom", b"Killed process", b"segfault", b"general protection", b"Call Trace",
                          b"I/O error", b"-fs error", b"XFS", b"blk_update", b"blocked for", b"hung_task", b"lockup",
                          b"LOCKUP", b"conntrack", b"Dropping", b"socket memory", b"throttling")}
    acc = Acc(keyfn=lambda t: float(t) if re.fullmatch(r"[\d.]+", t) else None, tz="boot")
    counts = scan_stream(path, "dmesg.txt", spec, acc, with_excerpts)
    first, last = window(path, starts_dmesg)
    acc.files.append({"file": "dmesg.txt", "size_bytes": os.path.getsize(path), "first": first, "last": last, **counts})
    return acc, []


def scan_stacks(root, with_excerpts):
    path = os.path.join(root, "stacks.txt")
    if not os.path.isfile(path):
        return {"present": False, "searched": ["stacks.txt"]}
    acc = Acc()
    states, header = {}, None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    for n, line in enumerate(lines, 1):
        if line.startswith('"'):
            header = line
        m = re.match(r"\s*java\.lang\.Thread\.State: (\w+)", line)
        if m:
            states[m.group(1)] = states.get(m.group(1), 0) + 1
            if m.group(1) == "BLOCKED" and header:
                name = re.match(r'"([^"]*)"', header)
                pattern = "Thread BLOCKED: " + re.sub(r"\d+", "N", mask(name.group(1) if name else "?"))
                acc.add("WARN", pattern, None, f"stacks.txt:{n}", "stacks.txt",
                        [clip(mask(x)) for x in lines[n - 2:n + 4]] if with_excerpts else [])
        if "Found one Java-level deadlock" in line:
            acc.add("ERROR", "Java-level deadlock", None, f"stacks.txt:{n}", "stacks.txt",
                    [clip(mask(x)) for x in lines[n - 1:n + 7]] if with_excerpts else [], sig="deadlock")
    acc.files.append({"file": "stacks.txt", "size_bytes": os.path.getsize(path), "first": ABSENT, "last": ABSENT,
                      **acc.totals})
    return acc, [], {"thread_states": dict(sorted(states.items()))}


def scan_hs_err(mirror, with_excerpts):
    base = os.path.join(mirror, "run")
    names = sorted(n for n in os.listdir(base) if re.fullmatch(r"hs_err_pid\d+\.log", n)) if os.path.isdir(base) else []
    if not names:
        return {"present": False, "searched": ["run/hs_err_pid*.log"]}
    acc = Acc(keyfn=lambda t: hs_parse(t)[0])
    for n in names:
        head = []
        with open(os.path.join(base, n), "r", encoding="utf-8", errors="replace") as fh:
            for _, line in zip(range(3000), fh):
                head.append(line.rstrip("\n"))
                if line.startswith("java_command:"):
                    break
        text = "\n".join(head)
        hashes = [ln.lstrip("# ").strip() for ln in head[:14] if ln.startswith("#") and ln.strip("# ")]
        problem = re.search(r"^#\s+(Out of Memory Error|Internal Error|SIG[A-Z]+)", text, re.M)
        when = re.search(r"^Time: (.+?)(?: elapsed time:.*)?$", text, re.M)
        cmd = re.search(r"^java_command: (\S+)", text, re.M)
        process = cmd.group(1).rsplit(".", 1)[-1] if cmd else "?"
        pattern = f"JVM crash ({problem.group(1) if problem else 'unknown'}) in {process}"
        iso_ts, zone = hs_parse(when.group(1)) if when else (None, None)
        entry = {"file": f"run/{n}", "size_bytes": os.path.getsize(os.path.join(base, n)),
                 "first": when.group(1) if when else ABSENT, "last": when.group(1) if when else ABSENT}
        if WIN.active and not WIN.keep(iso_ts):
            acc.files.append({**entry, "WARN": 0, "ERROR": 0, "FATAL": 0, "skipped_outside_window": True})
            continue
        sig = "oom" if problem and problem.group(1) == "Out of Memory Error" else "process_crash"
        acc.add("FATAL", pattern, when.group(1) if when else None, f"run/{n}:1", f"run/{n}",
                [clip(mask(h)) for h in hashes[:6]] if with_excerpts else [], sig=sig, iso_ts=iso_ts,
                tz=(zone or "unknown").lower() if zone in ("UTC", "GMT") else "local")
        acc.files.append({**entry, "WARN": 0, "ERROR": 0, "FATAL": 1})
    return acc, []


# ---- driver --------------------------------------------------------------------------------------------------------
LOG_IDS = list(SPECS) + ["codeenv", "dmesg", "stacks", "hs_err"]


def run_log(log_id, root, mirror, top, with_excerpts):
    if log_id in SPECS:
        res = scan_files(log_id, mirror, with_excerpts)
    elif log_id == "codeenv":
        res = scan_codeenv(mirror, with_excerpts)
    elif log_id == "dmesg":
        res = scan_dmesg(root, with_excerpts)
    elif log_id == "stacks":
        res = scan_stacks(root, with_excerpts)
    else:
        res = scan_hs_err(mirror, with_excerpts)
    if isinstance(res, dict):
        return res
    acc, skipped, *extra = res
    findings, not_listed = acc.findings(log_id, top, with_excerpts)
    out = {"present": True, "label": SPECS[log_id]["label"] if log_id in SPECS else log_id, "tz": acc.tz,
           "files": acc.files, "totals": acc.totals, "gz_files_skipped": len(skipped), "findings": findings,
           "findings_not_listed": not_listed, "patterns_uncounted": acc.overflow}
    if WIN.active:
        out["time_filter"] = "applied" if log_id in SPECS or log_id == "hs_err" else "not_applicable"
    if TIMELINE:
        out["_events"] = [{**ev, "log": log_id} for ev in acc.events]
        out["_events_untimed"] = acc.events_untimed
        out["_events_dropped"] = acc.events_dropped
    for x in extra:
        out.update(x)
    return out


def find_mirror(root):
    for dirpath, dirs, files in os.walk(root):
        if dirpath[len(root):].count(os.sep) > 6:
            dirs[:] = []
            continue
        if "install.ini" in files:
            return dirpath
    return None


def main():
    global WIN, TIMELINE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle_root")
    ap.add_argument("--log", action="append", choices=LOG_IDS, help="limit to this log (repeatable)")
    ap.add_argument("--top", type=int, default=30, help="findings kept per log, signature findings excepted (default 30)")
    ap.add_argument("--no-excerpts", action="store_true", help="patterns and counts only, no log text")
    ap.add_argument("--since", help="keep records at or after this ISO time or date")
    ap.add_argument("--until", help="keep records at or before this ISO time or date (a bare date means its whole day)")
    ap.add_argument("--around", help="ISO time; shorthand for --since/--until of this time -/+ --window")
    ap.add_argument("--window", default="30m", help="span for --around, e.g. 30m, 2h, 1d (default 30m)")
    ap.add_argument("--timeline", action="store_true", help="add one merged, time-sorted list of signature and FATAL events")
    args = ap.parse_args()
    if not os.path.isdir(args.bundle_root):
        sys.exit("Usage: logscan.py <bundle_root> [--log ID ...] [--top N] [--no-excerpts] [--since TS] [--until TS] "
                 "[--around TS [--window 30m]] [--timeline]")
    since = parse_when(args.since) if args.since else None
    until = parse_when(args.until, end=True) if args.until else None
    if args.around:
        centre, span = datetime.datetime.fromisoformat(parse_when(args.around)), parse_span(args.window)
        since = since or (centre - span).strftime("%Y-%m-%dT%H:%M:%S")
        until = until or (centre + span).strftime("%Y-%m-%dT%H:%M:%S")
    WIN, TIMELINE = Window(since, until), args.timeline
    root = os.path.abspath(args.bundle_root)
    mirror = find_mirror(root)
    if mirror is None:
        sys.exit("logscan.py: no install.ini found under the bundle (searched 6 levels deep)")
    logs, events, untimed, dropped = {}, [], {}, 0
    for log_id in args.log or LOG_IDS:
        try:
            logs[log_id] = run_log(log_id, root, mirror, args.top, not args.no_excerpts)
        except Exception as exc:  # noqa: BLE001 - one unreadable log must not stop the others
            logs[log_id] = {"present": True, "error": f"{type(exc).__name__}: {exc}"}
        events += logs[log_id].pop("_events", [])
        dropped += logs[log_id].pop("_events_dropped", 0)
        if logs[log_id].pop("_events_untimed", 0):
            untimed[log_id] = logs[log_id].get("totals", {})
    out = {"bundle_root": os.path.basename(root), "mirror": os.path.relpath(mirror, root), "logs": logs}
    if WIN.active:
        out["window"] = {"since": WIN.since, "until": WIN.until}
    if TIMELINE:
        events.sort(key=lambda ev: (ev["at"], ev["log"]))
        out["timeline"] = {"note": "times are each log's own clock (see tz); 'local' times carry no zone, so order across "
                                   "logs is approximate. dmesg is boot-relative and not on the timeline.",
                           "events": events[:TIMELINE_CAP], "events_not_listed": max(0, len(events) - TIMELINE_CAP) + dropped,
                           "logs_with_untimed_events": sorted(untimed)}
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
