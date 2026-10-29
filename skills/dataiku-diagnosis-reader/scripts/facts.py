#!/usr/bin/env python3
"""Key settings of a Dataiku diagnosis bundle in one deterministic, secret-safe JSON report.

Usage: facts.py <bundle_root>

Prints one JSON object, `{fact_name: {"value": ..., "source": "<path relative to the mirror>: <key>"}}`.
A setting that is not in the bundle is reported as `{"value": "ABSENT", "searched": [...]}`, so
"absent" is never confused with `false` or `0`. A fact that could not be read is reported as
`{"value": "ERROR", "error": "..."}`; one bad file never stops the others.

It exists so a reviewer quotes these values instead of re-reading a ~large general-settings.json by
hand (hand reads have mis-stated hosts, flags and limits, and missed keys that sit under an
unexpected block). Concurrency limits are found by leaf-key search of the whole file, so a limit under
`jekSettings` is not missed. The `config/` size comes from `config_listing.txt`, not `du`. The disk
behind the data directory comes from the `lsblk` blocks of `diag.txt`. Housekeeping-project scenarios are
summarised without ever opening a scenario's script, and the deployer target is reported without its API key.

Read-only; no network calls; Python 3 stdlib only. Passwords and other secrets are never printed
(only a boolean says whether the internal database password is stored in plaintext). Redaction reuses
`peek.py` when it sits next to this file, with a built-in fallback if it does not.
"""
import json
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from peek import describe_scalar
except ImportError:  # copied on its own: redact every string under a secret-looking key
    _SECRET = re.compile(r"pass|pwd|secret|token|key|credential|auth|cert|private|salt|hash", re.I)

    def describe_scalar(key, value):
        if isinstance(value, str) and key is not None and _SECRET.search(str(key)):
            return "<redacted>"
        return json.dumps(value)

ABSENT = "ABSENT"
CONCURRENCY_KEYS = ("maxRunningJobs", "maxRunningActivities", "maxRunningActivitiesPerJob")
LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]", "0.0.0.0"}
FACTS = {}


def safe(value, key=None):
    """JSON-ready value with strings run through the redaction used by peek.py."""
    if value == ABSENT:  # the marker is not a secret, even under a key name like "authenticationEnabled"
        return value
    if isinstance(value, str):
        shown = describe_scalar(key, value)
        try:
            return json.loads(shown)
        except ValueError:
            return shown
    return value


def fact(name):
    """Register a fact function; an exception becomes an ERROR entry for that fact only."""
    def deco(fn):
        def run():
            try:
                FACTS[name] = fn()
            except Exception as exc:  # noqa: BLE001 - one bad file must not abort the report
                FACTS[name] = {"value": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
        run.__name__ = fn.__name__
        RUNNERS.append(run)
        return run
    return deco


RUNNERS = []
ROOT = MIRROR = None


def found(value, source):
    return {"value": value, "source": source}


def absent(*searched):
    return {"value": ABSENT, "searched": list(searched)}


def load_json(rel):
    path = os.path.join(MIRROR, rel)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dig(node, dotted):
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return ABSENT
    return node


def leaf_search(node, names, path=""):
    """Every (dotted path, value) whose last key is in `names`, anywhere in the document."""
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}" if path else str(k)
            if k in names and not isinstance(v, (dict, list)):
                hits.append((p, v))
            hits.extend(leaf_search(v, names, p))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(leaf_search(v, names, f"{path}[{i}]"))
    return hits


def settings_fact(*dotted_paths):
    """Value of each dotted path in general-settings.json (ABSENT when missing)."""
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    return {"source": src, "value": {p: safe(dig(gs, p), p.rsplit(".", 1)[-1]) for p in dotted_paths}}


def parse_ini(path):
    """{'section.key': value} for an INI file, tolerant of odd lines (no configparser strictness)."""
    out, section = {}, ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line[0] in "#;":
                continue
            m = re.match(r"\[(.+)\]$", line)
            if m:
                section = m.group(1).strip()
            elif "=" in line:
                k, v = line.split("=", 1)
                out[f"{section}.{k.strip()}"] = v.strip()
    return out


def mem_total_kb():
    path = os.path.join(ROOT, "diag.txt")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"MemTotal:\s+(\d+)\s*kB", line)
            if m:
                return int(m.group(1))
    return None


def to_gib(text):
    """'190G' / '512M' / a byte count -> GiB, or None."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMGT]?)i?B?\s*", str(text), re.I)
    if not m:
        return None
    unit = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}[m.group(2).upper()]
    return float(m.group(1)) * unit / 1024 ** 3


@fact("node")
def node():
    ini = os.path.join(MIRROR, "install.ini")
    kv = parse_ini(ini)
    ver = load_json("dss-version.json") or {}
    pick = lambda k: next((v for key, v in kv.items() if key.split(".", 1)[1] == k), ABSENT)  # noqa: E731
    return found({"nodetype": pick("nodetype"), "nodeid": pick("nodeid"), "installid": pick("installid"),
                  "product_version": ver.get("product_version", ABSENT)}, "install.ini, dss-version.json")


@fact("heap_sizes")
def heap_sizes():
    kv = parse_ini(os.path.join(MIRROR, "install.ini"))
    xmx = {k: v for k, v in kv.items() if "xmx" in k.lower()}
    if not xmx:
        return absent("install.ini (no *.xmx key; DSS defaults apply)")
    return found(xmx, "install.ini")


@fact("host_memory")
def host_memory():
    kb = mem_total_kb()
    if kb is None:
        return absent("diag.txt MemTotal")
    return found({"MemTotal_kB": kb, "GiB": round(kb / 1024 / 1024, 1)}, "diag.txt: MemTotal")


@fact("config_folder_size")
def config_folder_size():
    rel = "config_listing.txt"
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return absent(rel)
    total = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            f = line.split(None, 10)
            if len(f) >= 11 and f[2].startswith("-") and f[6].isdigit():
                total += int(f[6])
    return found({"bytes": total, "MiB": round(total / 1024 ** 2, 1), "GiB": round(total / 1024 ** 3, 2)},
                 f"{rel}: sum of regular-file sizes (not du)")


@fact("internal_database")
def internal_database():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    conn = dig(gs, "internalDatabase.connection")
    if conn == ABSENT or not isinstance(conn, dict):
        return absent(f"{src}: internalDatabase.connection")
    params = conn.get("params") or {}
    host = params.get("host", ABSENT)
    pw = params.get("password")
    return found({
        "type": conn.get("type", ABSENT),
        "host": host,
        "host_is_loopback": (str(host).lower() in LOOPBACK) if host != ABSENT else ABSENT,
        "port": params.get("port", ABSENT),
        "password_stored_in_plaintext": (bool(pw) and not str(pw).startswith("e:")) if "password" in params else ABSENT,
    }, f"{src}: internalDatabase.connection (password value never printed)")


@fact("concurrency_limits")
def concurrency_limits():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    value = {}
    for name in CONCURRENCY_KEYS:
        hits = [{"path": p, "value": v} for p, v in leaf_search(gs, {name})]
        value[name] = hits or ABSENT
    return found(value, f"{src}: leaf-key search of the whole file (a 0 under jekSettings means unsized)")


@fact("sso_and_ldap")
def sso_and_ldap():
    res = settings_fact("ssoSettings.enabled", "ssoSettings.protocol",
                        "ldapSettings.enabled", "ldapSettings.authenticationEnabled")
    if isinstance(res.get("value"), dict):  # authorized groups: the count only, group names are not printed
        groups = dig(load_json("config/general-settings.json"), "ldapSettings.authorizedGroups")
        res["value"]["ldapSettings.authorizedGroups_count"] = len(groups) if isinstance(groups, list) else groups
    return res


@fact("byo_llm")
def byo_llm():
    """Bring Your Own LLM mode: active when a main LLM id or a reference project key is set. A CustomLLM
    connection alone does not make it active. Field names come from Dataiku's checklist; no sample bundle
    has them populated yet, so an unset block reads as inactive."""
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    block = dig(gs, "localAIServerSettings")
    if block == ABSENT:
        return absent(f"{src}: localAIServerSettings")
    get = lambda k: (block.get(k) or ABSENT) if isinstance(block, dict) else ABSENT  # noqa: E731
    main, ref = get("mainLLMId"), get("referenceProjectKey")
    return found({"active": main != ABSENT or ref != ABSENT, "mainLLMId": main, "referenceProjectKey_set": ref != ABSENT,
                  "responseFormatAwareLLMId": get("responseFormatAwareLLMId"), "fastLightLLMId": get("fastLightLLMId")},
                 f"{src}: localAIServerSettings (model ids are names, not secrets; empty or missing reads ABSENT)")


@fact("sanity_check")
def sanity_check():
    """Whether DSS's own sanity-check output is in the bundle (`empty` is true for a blank file or no messages),
    its message counts by severity, and the distinct message codes (fixed identifiers like WARN_PROJECT_LARGE_JOB_HISTORY;
    the free-text `details` is never printed)."""
    src = "run/sanity-check.json"
    if not os.path.isfile(os.path.join(MIRROR, src)):
        return absent(src)
    try:
        doc = load_json(src)
    except ValueError:  # a blank or unparseable file counts as empty output
        doc = None
    if not isinstance(doc, dict):
        return found({"present": True, "empty": True, "messages": 0, "by_severity": {}, "fatal": 0, "codes": []},
                     f"{src} (file is blank or not a JSON object)")
    report = doc.get("report") if isinstance(doc.get("report"), dict) else doc  # nested in one sample layout
    msgs = report.get("messages") if isinstance(report, dict) else None
    by_severity, codes = {}, set()
    for m in msgs if isinstance(msgs, list) else []:
        sev = str((m or {}).get("severity", "UNKNOWN")) if isinstance(m, dict) else "UNKNOWN"
        by_severity[sev] = by_severity.get(sev, 0) + 1
        if isinstance(m, dict) and (m.get("code") or m.get("title")):
            codes.add(str(m.get("code") or m.get("title")))
    return found({"present": True, "empty": not msgs, "messages": len(msgs) if isinstance(msgs, list) else ABSENT,
                  "by_severity": by_severity, "fatal": sum(1 for m in msgs or [] if isinstance(m, dict) and m.get("isFatal")),
                  "codes": sorted(codes)},
                 f"{src} (the last-run time is only the file's mtime unless the file carries lastRunTimestamp)")


SECURITY_KEYS = ("hideErrorStacks", "hideVersionStringsWhenNotLogged", "sessionsMaxTotalTimeMinutes", "sessionsMaxIdleTimeMinutes",
                 "forceSingleSessionPerUser", "restrictUsersAndGroupsVisibility", "postLogoutBehavior", "sameSiteNoneCookies",
                 "secureCookies", "enableEmailAndDisplayNameModification", "disableDataTableLinks")


@fact("security_settings")
def security_settings():
    """The instance's security toggles from `general-settings.json` > `security`, whitelisted keys only. The custom
    post-logout URL is reduced to its scheme (`postLogoutCustomURL_scheme`: http, https, other, or ABSENT when unset)."""
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    sec = dig(gs, "security")
    if sec == ABSENT or not isinstance(sec, dict):
        return absent(f"{src}: security")
    out = {k: (sec[k] if isinstance(sec.get(k), (bool, int, str)) else ABSENT) for k in SECURITY_KEYS}
    url = sec.get("postLogoutCustomURL")
    out["postLogoutCustomURL_scheme"] = (ABSENT if not isinstance(url, str) or not url.strip()
                                         else url.split(":", 1)[0].lower() if url.lower().startswith(("http://", "https://")) else "other")
    return found(out, f"{src}: security (whitelisted keys; a custom logout URL is reduced to its scheme)")


SECURITY_HEADERS = ("content-security-policy", "x-frame-options", "x-content-type-options", "x-xss-protection", "hsts-max-age",
                    "referrer-policy", "permissions-policy", "cross-origin-embedder-policy", "cross-origin-opener-policy",
                    "cross-origin-resource-policy")
EXPORT_KEYS = ("dku.exports.disableAllDatasetExports", "dku.exports.disableAllDataExports", "dku.exports.disableAllExports",
               "dku.exports.disableCopySampleToClipboard", "dku.exports.disableSQLNotebookCopyResultToClipboard")
WIKI_UPLOAD_KEY = "dku.wikis.authorizedUploadExtensions"
TABLE_LINKS_KEY = "dku.feature.dataTableLinks.enabled"


def parse_properties(path):
    """{key: value} for a Java .properties file (key=value lines; # and ! start comments)."""
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if line and line[0] not in "#!" and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


@fact("server_config")
def server_config():
    """Whitelisted settings from `install.ini` [server] (HTTPS and the security headers) and `config/dip.properties`
    (export restrictions, wiki upload extensions, data-table links). Certificate and key locations are reduced to
    yes/no; header values are cut at 200 characters. `dip_properties_present` is false when the file is not in the
    bundle: DSS only has it once someone customised the instance, so an absent file means none of its keys are set."""
    ini_path = os.path.join(MIRROR, "install.ini")
    if not os.path.isfile(ini_path):
        return absent("install.ini")
    ini = parse_ini(ini_path)
    dip_path = os.path.join(MIRROR, "config", "dip.properties")
    dip_present = os.path.isfile(dip_path)
    dip = parse_properties(dip_path) if dip_present else {}
    headers = {h: ini[f"server.{h}"][:200] for h in SECURITY_HEADERS if ini.get(f"server.{h}")}
    return found({
        "ssl": ini.get("server.ssl", ABSENT),
        "ssl_certificate_configured": bool(ini.get("server.ssl_certificate")),
        "security_headers": headers,
        "dip_properties_present": dip_present,
        "exports": {k: dip[k] for k in EXPORT_KEYS if k in dip},
        "wiki_upload_extensions": dip.get(WIKI_UPLOAD_KEY, ABSENT),
        "data_table_links_enabled": dip.get(TABLE_LINKS_KEY, ABSENT),
    }, "install.ini [server], config/dip.properties (whitelisted keys; certificate paths reduced to yes/no)")


@fact("user_isolation")
def user_isolation():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    imp = dig(gs, "impersonation")
    if imp == ABSENT:
        return absent(f"{src}: impersonation")
    return found({"enabled": imp.get("enabled", ABSENT), "user_rules": len(imp.get("userRules") or []),
                  "group_rules": len(imp.get("groupRules") or [])},
                 f"{src}: impersonation (rule counts only, account names not printed)")


@fact("cgroups")
def cgroups():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    cg = dig(gs, "cgroupSettings")
    if cg == ABSENT:
        return absent(f"{src}: cgroupSettings")
    kb = mem_total_kb()
    placements_empty = [k for k, v in cg.items() if isinstance(v, dict) and not v.get("targets")]
    # target count per workload category that has a `targets` list; a category absent here is not configured at all
    target_counts = {k: len(v["targets"]) for k, v in cg.items()
                     if isinstance(v, dict) and isinstance(v.get("targets"), list)}
    limits = []
    for entry in cg.get("cgroups") or []:
        for lim in entry.get("limits") or []:
            gib = to_gib(lim.get("value"))
            limits.append({
                "cgroup": entry.get("cgroupPathTemplate"), "limit": lim.get("key"), "value": lim.get("value"),
                "pct_of_MemTotal": round(100 * gib / (kb / 1024 / 1024), 1) if gib and kb and "memory" in str(lim.get("key")) else None,
            })
    return found({"enabled": cg.get("enabled", ABSENT), "version": cg.get("cgroupsVersion", ABSENT),
                  "limits": limits or ABSENT, "workload_categories_with_no_placement": placements_empty,
                  "target_counts": target_counts},
                 f"{src}: cgroupSettings (pct uses G=GiB against diag.txt MemTotal in GiB)")


CLOUD_STORAGE_TYPES = {"s3": "s3", "azure": "azure", "gcs": "gcs"}
WAREHOUSE_TYPES = {"snowflake": "snowflake", "databricks": "databricks", "redshift": "redshift", "bigquery": "bigquery",
                   "synapse": "synapse"}
_NOT_A_TOGGLE = ("identity", "auth", "credential")


def _is_set(value):
    """A connection setting counts as set when it holds a value: true, a non-blank string other than NONE/false, a non-empty list or dict."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ("", "none", "false")
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def _flag(params, needles):
    """Whether a feature is set on a connection when its setting name is not known in advance: any param whose
    normalised key contains one of `needles` (identity and credential options excluded) and holds a value counts as set.
    True if any such param is set, False if some exist and none is, ABSENT when no param name matches."""
    hits = []
    for key, value in params.items():
        norm = re.sub(r"[^a-z0-9]", "", str(key).lower())
        if any(n in norm for n in needles) and not any(x in norm for x in _NOT_A_TOGGLE):
            hits.append(_is_set(value))
    return ABSENT if not hits else any(hits)


@fact("connections")
def connections():
    src = "config/connections.json"
    doc = load_json(src)
    if doc is None:
        return absent(src)
    conns = doc.get("connections", doc) if isinstance(doc, dict) else {}
    cloud_storage, warehouses = [], []
    for conn in conns.values() if isinstance(conns, dict) else []:
        if not isinstance(conn, dict):
            continue
        ctype, params = str(conn.get("type", "")).lower(), conn.get("params")
        params = params if isinstance(params, dict) else {}
        if ctype in CLOUD_STORAGE_TYPES:
            readable = (conn.get("detailsReadability") or {}).get("readableBy", ABSENT) if isinstance(conn.get("detailsReadability"), dict) else ABSENT
            hdfs = params.get("hdfsInterface", ABSENT)
            cloud_storage.append({"type": CLOUD_STORAGE_TYPES[ctype],
                                  "readable_by_set": ABSENT if readable == ABSENT else str(readable).upper() != "NONE",
                                  "hdfs_interface_set": ABSENT if hdfs == ABSENT else _is_set(hdfs)})
        kind = WAREHOUSE_TYPES.get(ctype)
        if ctype == "sqlserver" and params.get("azureDWH") is True:
            kind = "synapse"
        if kind:
            warehouses.append({"type": kind, "fast_write": _flag(params, ("fastwrite", "fastpath")),
                               "spark_native": _flag(params, ("sparknative", "sparkintegration")),
                               "udf": _flag(params, ("udf",))})
    return found({"count": len(conns), "filesystem_root_present": "filesystem_root" in conns,
                  "cloud_storage": cloud_storage, "warehouses": warehouses},
                 f"{src}: connections (types and booleans only, no params)")


@fact("trace_explorer")
def trace_explorer():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    hits = leaf_search(gs, {"projectKey", "webAppId"}, "")
    hits = [(p, v) for p, v in hits if "traceExplorerDefaultWebApp" in p]
    trace = dig(gs, "generativeAISettings.llmTraceSettings")
    if not hits:
        return found({"configured": False, "llmTraceSettings": safe(trace)} if trace != ABSENT
                     else ABSENT, f"{src}: generativeAISettings.llmTraceSettings")
    return found({"configured": all(v for _, v in hits), "fields": {p: v for p, v in hits}},
                 f"{src}: generativeAISettings.llmTraceSettings.traceExplorerDefaultWebApp")


AI_SERVICES_FLAGS = ("enabled", "prepareAICompletionEnabled", "aiGenerateSQLEnabled", "aiExplanationsEnabled", "storiesAIEnabled")
COBUILD_KEYS = ("defaultEmbeddingLLMId", "defaultLLMId", "defaultImageGenerationLLMId")


@fact("genai_settings")
def genai_settings():
    """GenAI settings from `general-settings.json`: the default code envs for retrieval (RAG) and PII detection (env names,
    not secrets; an unset or empty value reads ABSENT), whether the AI Services terms are accepted and which AI features are
    enabled, and which Cobuild default LLM ids are set (set or not only; the ids are not printed). Field names for the
    Cobuild block come from Dataiku's checklist; no sample bundle carries it yet, so it reads ABSENT there."""
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    gen, ai = dig(gs, "generativeAISettings"), dig(gs, "aiDrivenAnalyticsSettings")
    if gen == ABSENT and ai == ABSENT:
        return absent(f"{src}: generativeAISettings, aiDrivenAnalyticsSettings")
    env = lambda k: (gen.get(k) if isinstance(gen, dict) and isinstance(gen.get(k), str) and gen.get(k).strip() else ABSENT)  # noqa: E731
    flag = lambda k: (ai.get(k) if isinstance(ai, dict) and isinstance(ai.get(k), bool) else ABSENT)  # noqa: E731
    build = dig(ai, "agentBuildingSettings") if isinstance(ai, dict) else ABSENT
    cobuild = (ABSENT if not isinstance(build, dict)
               else {k: bool(isinstance(build.get(k), str) and build.get(k).strip()) for k in COBUILD_KEYS})
    return found({"generativeAISettings_present": gen != ABSENT, "retrieval_code_env": env("defaultRetrievableKnowledgeCodeEnv"),
                  "pii_detection_code_env": env("presidioBasedPIIDetectionCodeEnv"),
                  "ai_services_terms_accepted": flag("dataikuAIServicesTermsOfUseAccepted"),
                  "ai_services_enabled": {k: flag(k) for k in AI_SERVICES_FLAGS},
                  "cobuild_default_llms_set": cobuild},
                 f"{src}: generativeAISettings, aiDrivenAnalyticsSettings (code env names; Cobuild LLM ids reduced to set/unset)")


@fact("metastore_and_exports")
def metastore_and_exports():
    """The metastore catalog flavor, the estate signals that decide whether it fits (Hive enabled, Hadoop in the host
    environment), and whether graphics (PDF/image) export is on. A key that is not set reads ABSENT, never false."""
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    flavor = dig(gs, "metastoreCatalogsSettings.synchronizeTo.flavor")
    hive = dig(gs, "hiveSettings.enabled")
    graphics = gs.get("graphicsExportsEnabled")
    hadoop_env = diag_env("DKU_HADOOP_ENABLED")
    return found({"metastore_flavor": flavor if isinstance(flavor, str) and flavor else ABSENT,
                  "hive_enabled": hive if isinstance(hive, bool) else ABSENT,
                  "hadoop_enabled_in_host_env": (hadoop_env.lower() == "true") if hadoop_env is not None else ABSENT,
                  "graphics_exports_enabled": graphics if isinstance(graphics, bool) else ABSENT},
                 f"{src}: metastoreCatalogsSettings, hiveSettings, graphicsExportsEnabled; diag.txt: DKU_HADOOP_ENABLED")


LOG_LINE = re.compile(rb"^\[(\d{4}/\d\d/\d\d-\d\d:\d\d:\d\d)[.\d]*\] \[[^\]]*\] \[([A-Z]+)\]")
RUN_AS_MISSING = re.compile(rb"Cannot run scenario ([\w.-]+): configured to run as user '([^']*)' which does not exist")
PATTERN_CAP, PATTERN_TOP, PATTERN_WIDTH = 500, 10, 120
CRASH_DUMP_LINES = 3000


_LOGSCAN = []


def _logscan():
    """`logscan.py` next to this file, loaded by path so it works under `python -I`; None if it is missing."""
    if not _LOGSCAN:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logscan.py")
        mod = None
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("logscan", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        _LOGSCAN.append(mod)
    return _LOGSCAN[0]


def error_pattern(rest):
    """A stable key for an ERROR/FATAL line: the logger plus the message's first clause, masked and normalised exactly as
    `logscan.py` does (emails, hosts, users, project keys, ids, quoted text, numbers), so repeats of one failure group together
    and the text carries no identifiers. `rest` is the line after the level token. Without `logscan.py` beside this file only
    the logger is kept."""
    m = re.match(r"\s*\[([^\]]*)\]\s*(?:-\s*)?(.*)", rest.decode("utf-8", "replace"), re.S)
    logger, msg = (m.group(1), m.group(2)) if m else ("", rest.decode("utf-8", "replace"))
    ls = _logscan()
    return f"[{logger}] {ls.normalise(msg) if ls else ''}".strip()[:PATTERN_WIDTH]


@fact("backend_log")
def backend_log():
    """Counts per backend log file (`backend.log`, `.1`, `.2`, ...): lines at ERROR, FATAL and WARN, lines naming an
    OutOfMemoryError, and the file's first and last timestamp, so every count carries its window. Streams each file line by
    line (they run to ~100MB) and prints counts plus masked, normalised error patterns (no raw log lines). Compressed rotations are not read (`gz_files_skipped`)."""
    rel = "run"
    base = os.path.join(MIRROR, rel)
    if not os.path.isdir(base):
        return absent(rel)
    names = sorted((n for n in os.listdir(base) if re.fullmatch(r"backend\.log(\.\d+)?", n)),
                   key=lambda n: int(n.rsplit(".", 1)[1]) if n.count(".") == 2 else -1)
    gz = sorted(n for n in os.listdir(base) if re.fullmatch(r"backend\.log.*\.(gz|zip)", n))
    if not names:
        return absent(f"{rel}/backend.log*")
    files = []
    patterns, overflow = {}, 0
    run_as = {"count": 0, "scenarios": {}, "users": set(), "first": None, "last": None}
    for n in names:
        counts = {"ERROR": 0, "FATAL": 0, "WARN": 0}
        oom, first, last = 0, None, None
        with open(os.path.join(base, n), "rb") as fh:
            for line in fh:
                m = LOG_LINE.match(line)
                if m:
                    ts = m.group(1).decode()
                    first = first or ts
                    last = ts
                    lvl = m.group(2).decode()
                    if lvl in counts:
                        counts[lvl] += 1
                    if lvl in ("ERROR", "FATAL"):
                        key = error_pattern(line[m.end():])
                        if key in patterns or len(patterns) < PATTERN_CAP:
                            e = patterns.setdefault(key, {"count": 0, "first": ts, "last": ts})
                            e["count"] += 1
                            e["first"], e["last"] = min(e["first"], ts), max(e["last"], ts)
                        else:
                            overflow += 1
                        r = RUN_AS_MISSING.search(line)
                        if r:
                            run_as["count"] += 1
                            sc = run_as["scenarios"].setdefault(r.group(1).decode(), 0)
                            run_as["scenarios"][r.group(1).decode()] = sc + 1
                            run_as["users"].add(r.group(2))
                            run_as["first"] = min(run_as["first"] or ts, ts)
                            run_as["last"] = max(run_as["last"] or ts, ts)
                if b"OutOfMemoryError" in line:
                    oom += 1
        files.append({"file": n, **counts, "OutOfMemoryError": oom, "first": first or ABSENT, "last": last or ABSENT})
    total = lambda k: sum(f[k] for f in files)  # noqa: E731
    errors = total("ERROR") + total("FATAL")
    top = sorted(patterns.items(), key=lambda kv: (-kv[1]["count"], kv[0]))[:PATTERN_TOP]
    top_patterns = [{"pattern": k, "count": v["count"], "share_pct": round(100 * v["count"] / errors, 1) if errors else 0,
                     "first": v["first"], "last": v["last"]} for k, v in top]
    run_as_missing = {"count": run_as["count"], "distinct_users": len(run_as["users"]),
                      "scenarios": dict(sorted(run_as["scenarios"].items())), "first": run_as["first"] or ABSENT,
                      "last": run_as["last"] or ABSENT}
    return found({"files": files, "ERROR": total("ERROR"), "FATAL": total("FATAL"), "WARN": total("WARN"),
                  "OutOfMemoryError": total("OutOfMemoryError"), "gz_files_skipped": len(gz),
                  "top_error_patterns": top_patterns, "error_patterns_uncounted": overflow,
                  "run_as_user_missing": run_as_missing},
                 f"{rel}/backend.log*: line counts by level, OutOfMemoryError mentions, the most frequent ERROR/FATAL messages "
                 "(normalised, truncated) and run-as-user-missing errors (user names never printed)")


@fact("crash_dumps")
def crash_dumps():
    """JVM fatal crash dumps (`run/hs_err_pid*.log`): per dump the process (the main class's name), the cause line, the
    problem class (e.g. Out of Memory Error, Internal Error) and when it happened. Reads each dump only down to its `java_command:` line."""
    rel = "run"
    base = os.path.join(MIRROR, rel)
    if not os.path.isdir(base):
        return absent(rel)
    names = sorted(n for n in os.listdir(base) if re.fullmatch(r"hs_err_pid\d+\.log", n))
    dumps = []
    for n in names[:20]:
        head = []
        with open(os.path.join(base, n), "r", encoding="utf-8", errors="replace") as fh:
            for _, line in zip(range(CRASH_DUMP_LINES), fh):  # the header, then up to the VM arguments' java_command
                head.append(line.rstrip("\n"))
                if line.startswith("java_command:"):
                    break
        text = "\n".join(head)
        hashes = [ln.lstrip("# ").strip() for ln in head[:12] if ln.startswith("#") and ln.strip("# ")]
        problem = re.search(r"^#\s+(Out of Memory Error|Internal Error|SIG[A-Z]+)", text, re.M)
        when = re.search(r"^Time: (.+?)(?: elapsed time:.*)?$", text, re.M)
        cmd = re.search(r"^java_command: (\S+)", text, re.M)
        dumps.append({"file": n, "process": cmd.group(1).rsplit(".", 1)[-1] if cmd else ABSENT,
                      "cause": hashes[0] if hashes else ABSENT, "problem": problem.group(1) if problem else ABSENT,
                      "time": when.group(1).strip() if when else ABSENT})
    return found({"count": len(names), "dumps": dumps},
                 f"{rel}/hs_err_pid*.log: header lines and java_command only (cause, problem class, time, process)")


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else ABSENT


def _namespace_kind(ns):
    """How a namespace field is set, without printing it: templated (a ${...} variable), fixed (a literal name) or ABSENT."""
    if not isinstance(ns, str) or not ns.strip():
        return ABSENT
    return "templated" if "${" in ns else "fixed"


@fact("kubernetes")
def kubernetes():
    """Kubernetes/Elastic Compute and Spark settings, reduced to what the checks judge: whether a cluster is attached
    (a `config/clusters/*.json` file or a default cluster id), each container and Spark execution config's sizing and
    namespace kind, and the container defaults (default and visual-recipe execution configs, containerized visual recipes).
    Names and numbers only: no registry URLs, secrets or literal namespace names."""
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    cdir = os.path.join(MIRROR, "config", "clusters")
    files = sorted(n for n in os.listdir(cdir) if n.endswith(".json")) if os.path.isdir(cdir) else []
    clusters = []
    for n in files:
        try:
            with open(os.path.join(cdir, n), encoding="utf-8") as fh:
                c = json.load(fh)
            clusters.append({"type": c.get("type", ABSENT), "architecture": c.get("architecture", ABSENT)})
        except (OSError, ValueError):
            clusters.append({"type": "ERROR", "architecture": "ERROR"})
    default_cluster = gs.get("defaultK8sClusterId")
    cs, sp = gs.get("containerSettings"), gs.get("sparkSettings")
    cs, sp = (cs if isinstance(cs, dict) else {}), (sp if isinstance(sp, dict) else {})
    containers = []
    for e in cs.get("executionConfigs") or []:
        r = e.get("kubernetesResources") if isinstance(e.get("kubernetesResources"), dict) else {}
        containers.append({"name": e.get("name", ABSENT), "type": e.get("type", ABSENT),
                           "mem_request_mb": _num(r.get("memRequestMB")), "mem_limit_mb": _num(r.get("memLimitMB")),
                           "cpu_request": _num(r.get("cpuRequest")), "cpu_limit": _num(r.get("cpuLimit")),
                           "namespace": _namespace_kind(e.get("kubernetesNamespace"))})
    spark = []
    for e in sp.get("executionConfigs") or []:
        conf = {c.get("key"): c.get("value") for c in e.get("conf") or [] if isinstance(c, dict)}
        k = e.get("kubernetesSettings") if isinstance(e.get("kubernetesSettings"), dict) else {}
        spark.append({"name": e.get("name", ABSENT), "resources_set": any(str(key).startswith(("spark.executor.", "spark.driver.")) for key in conf),
                      **{key.split(".", 1)[1].replace(".", "_"): conf.get(key, ABSENT)
                         for key in ("spark.executor.instances", "spark.executor.memory", "spark.executor.cores", "spark.driver.memory")},
                      "managed_kubernetes": k.get("managedKubernetes", ABSENT),
                      "namespace": _namespace_kind(k.get("managedNamespace")), "authentication_mode": k.get("authenticationMode", ABSENT)})
    flag = lambda v: v if isinstance(v, bool) else ABSENT  # noqa: E731
    return found({"cluster_attached": bool(clusters) or (isinstance(default_cluster, str) and bool(default_cluster.strip())),
                  "cluster_files": clusters, "default_cluster_set": isinstance(default_cluster, str) and bool(default_cluster.strip()),
                  "implicit_cluster": flag(gs.get("useImplicitK8sCluster")),
                  "container_configs": containers,
                  "default_execution_config": (cs["defaultExecutionConfig"].strip() if isinstance(cs.get("defaultExecutionConfig"), str)
                                               and cs["defaultExecutionConfig"].strip() else ABSENT),
                  "default_visual_recipes_config_set": bool(isinstance(cs.get("defaultExecutionConfigForVisualRecipesWorkloads"), str)
                                                            and cs["defaultExecutionConfigForVisualRecipesWorkloads"].strip()),
                  "containerized_visual_recipes_enabled": flag(cs.get("cdeEnabled")),
                  "spark_enabled": flag(sp.get("sparkEnabled")), "spark_configs": spark},
                 f"{src}: containerSettings, sparkSettings, defaultK8sClusterId; config/clusters/*.json (type and architecture only)")


@fact("default_preferences")
def default_preferences():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    names = ("preferedConnection", "forcedPreferedConnection", "preferedUploadConnection", "preferedStorageFormats")
    dflt = dig(gs, "defaultDatasetCreationSettings")
    engines = dig(gs, "recipeEnginesPreferences")
    return found({
        "defaultDatasetCreationSettings": {n: (safe(dflt.get(n, ABSENT), n) if isinstance(dflt, dict) else ABSENT) for n in names},
        "recipeEnginesPreferences_nonempty": ({k: v for k, v in engines.items() if v} if isinstance(engines, dict) else ABSENT),
    }, f"{src}: defaultDatasetCreationSettings, recipeEnginesPreferences (key ABSENT or empty = blank)")


@fact("plugins")
def plugins():
    rel = "config/plugins"
    path = os.path.join(MIRROR, rel)
    if not os.path.isdir(path):
        return absent(rel)
    names = sorted(d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)))
    return found({"installed_config_dirs": names, "agent_hub_installed": "agent-hub" in names,
                  "AGENT_HUB_project_present": os.path.isdir(os.path.join(MIRROR, "config/projects/AGENT_HUB"))},
                 f"{rel}: directory names (agent_hub_installed = an agent-hub dir exists)")


def diag_section(cmd):
    """Lines of the `> <cmd>` block in diag.txt (up to the next `> ` command or a dashed separator)."""
    path = os.path.join(ROOT, "diag.txt")
    if not os.path.isfile(path):
        return None
    out, inside = [], False
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if inside and (line.startswith("> ") or line.startswith("-----")):
                break
            if inside:
                out.append(line)
            elif line.strip() == f"> {cmd}":
                inside = True
    return out if inside else None


def diag_env(name):
    path = os.path.join(ROOT, "diag.txt")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith(name + "="):
                return line.rstrip("\n").split("=", 1)[1].strip()
    return None


def lsblk_nodes(lines):
    """[{name, col, type, mount}] in listing order, from `lsblk` tree output (col = indent of the name)."""
    nodes = []
    for line in lines[1:]:
        m = re.search(r"[A-Za-z0-9_]", line)
        if not m:
            continue
        col = m.start()
        rest = line[col:]
        name = rest.split()[0]
        tail = re.match(r"\S+\s+\d+:\d+\s+\d\s+\S+\s+\d\s+(\S+)\s*(.*)$", rest)
        if not tail:
            continue
        nodes.append({"name": name, "col": col, "type": tail.group(1), "mount": tail.group(2).strip()})
    return nodes


def lsblk_rota(lines):
    """{device name: ROTA} from `lsblk -t` output, located by the ROTA column of the header."""
    header = lines[0].split()
    if "ROTA" not in header:
        return {}
    idx = header.index("ROTA")
    rota = {}
    for line in lines[1:]:
        m = re.search(r"[A-Za-z0-9_]", line)
        if not m:
            continue
        toks = line[m.start():].split()
        if len(toks) > idx and toks[idx] in ("0", "1"):
            rota[toks[0]] = int(toks[idx])
    return rota


@fact("data_volume_device")
def data_volume_device():
    src = "diag.txt: printenv DIP_HOME, lsblk, lsblk -t"
    data_dir = diag_env("DIP_HOME")
    tree, tuning = diag_section("lsblk"), diag_section("lsblk -t")
    if not data_dir or tree is None or tuning is None:
        return absent("diag.txt DIP_HOME" if not data_dir else "diag.txt lsblk / lsblk -t blocks")
    nodes = lsblk_nodes(tree)
    rota = lsblk_rota(tuning)
    best = None
    for n in nodes:
        mp = n["mount"]
        if mp.startswith("/") and (data_dir == mp or data_dir.startswith(mp.rstrip("/") + "/")):
            if best is None or len(mp) > len(best):
                best = mp
    if best is None:
        return absent(f"{src}: no lsblk mount point contains {data_dir}")
    disks = {}
    for i, n in enumerate(nodes):
        if n["mount"] != best:
            continue
        # walk up to the root disk of this listing entry (lsblk repeats an LVM volume under each disk)
        col = n["col"]
        for j in range(i - 1, -1, -1):
            if nodes[j]["col"] < col:
                col = nodes[j]["col"]
                if nodes[j]["col"] == 0:
                    disks.setdefault(nodes[j]["name"], rota.get(nodes[j]["name"]))
                    break
        if n["col"] == 0:
            disks.setdefault(n["name"], rota.get(n["name"]))
    if not disks:
        return absent(f"{src}: mount {best} has no backing disk in the listing")
    backing = [{"disk": d, "rota": r if r is not None else ABSENT} for d, r in sorted(disks.items())]
    known = [b["rota"] for b in backing if b["rota"] != ABSENT]
    return found({"data_dir": data_dir, "mount_point": best, "backing_disks": backing,
                  "all_non_rotational": (all(r == 0 for r in known) if len(known) == len(backing) else ABSENT)},
                 f"{src} (ROTA 0 = non-rotational/SSD, 1 = rotational)")


@fact("admin_cleanup_scenarios")
def admin_cleanup_scenarios():
    rel = "config/projects"
    base = os.path.join(MIRROR, rel)
    if not os.path.isdir(base):
        return absent(rel)
    cand = sorted(k for k in os.listdir(base)
                  if re.search(r"admin|maint|housekeep|clean", k, re.I) and os.path.isdir(os.path.join(base, k)))
    projects = {}
    for key in cand[:20]:
        sdir = os.path.join(base, key, "scenarios")
        scenarios = []
        for fn in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
            if not fn.endswith(".json"):
                continue  # a scenario's .py script is never opened
            try:
                with open(os.path.join(sdir, fn), encoding="utf-8") as fh:
                    sc = json.load(fh)
            except (OSError, ValueError) as exc:
                scenarios.append({"file": fn, "error": f"{type(exc).__name__}"})
                continue
            steps = (sc.get("params") or {}).get("steps") or []
            scenarios.append({
                "file": fn, "type": sc.get("type", ABSENT), "scripted": sc.get("type") != "step_based", "active": sc.get("active", ABSENT),
                "triggers": [{"type": t.get("type"), "active": t.get("active")} for t in sc.get("triggers") or []],
                "step_names": [st.get("name") or st.get("type") for st in steps][:12],
            })
        projects[key] = scenarios
    return found({"candidate_projects": projects, "candidate_count": len(cand)},
                 f"{rel}/<key>/scenarios/*.json (candidates matched on the key: admin, maint, housekeep, clean; scripts not read)")


@fact("deployer")
def deployer():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    d = dig(gs, "deployerClientSettings")
    if d == ABSENT or not isinstance(d, dict):
        return absent(f"{src}: deployerClientSettings")
    url = urlparse(d.get("nodeUrl") or "")
    mode = d.get("mode", ABSENT)
    return found({"mode": mode,
                  "remote_host_with_local_mode": bool(url.hostname) and isinstance(mode, str) and mode.upper() == "LOCAL",
                  "target_host": (url.hostname + (f":{url.port}" if url.port else "")) if url.hostname else ABSENT,
                  "api_key_configured": bool(d.get("apiKey")) if "apiKey" in d else ABSENT,
                  "trust_all_ssl_certificates": d.get("trustAllSSLCertificates", ABSENT)},
                 f"{src}: deployerClientSettings (API key value and URL credentials never printed)")


@fact("groups")
def groups():
    src = "config/users.json"
    doc = load_json(src)
    if not isinstance(doc, dict) or not isinstance(doc.get("groups"), list):
        return absent(f"{src}: groups")
    gl = [g for g in doc["groups"] if isinstance(g, dict)]
    src_types = {}
    for g in gl:
        key = str(g.get("sourceType", ABSENT))
        src_types[key] = src_types.get(key, 0) + 1
    return found({"count": len(gl),
                  "admin_groups": sum(1 for g in gl if g.get("admin") is True),
                  "may_create_projects": sum(1 for g in gl if g.get("mayCreateProjects") is True),
                  "may_manage_udm": sum(1 for g in gl if g.get("mayManageUDM") is True),
                  "by_source_type": src_types},
                 f"{src}: groups (counts only, group and user names not printed)")


@fact("local_deployer")
def local_deployer():
    base = os.path.join(MIRROR, "config")

    def count(rel):
        path = os.path.join(base, rel)
        if not os.path.isdir(path):
            return ABSENT
        return sum(1 for n in os.listdir(path) if n.endswith(".json"))

    counts = {"project_deployer_projects": count("project-deployer/projects"),
              "project_deployer_infras": count("project-deployer/infras"),
              "project_deployer_deployments": count("project-deployer/deployments"),
              "api_deployer_infras": count("api-deployer/infras"),
              "api_deployer_services": count("api-deployer/published-services"),
              "api_deployer_deployments": count("api-deployer/deployments")}
    if all(v == ABSENT for v in counts.values()):
        return absent("config/project-deployer", "config/api-deployer")
    return found(counts, "config/project-deployer/{projects,infras,deployments}, config/api-deployer/{infras,published-services,deployments} "
                         "(file counts only, names not printed; ABSENT = directory missing)")


def find_mirror(root):
    for dirpath, dirs, files in os.walk(root):
        if dirpath[len(root):].count(os.sep) > 6:
            dirs[:] = []
            continue
        if "install.ini" in files:
            return dirpath
    return None


def main():
    global ROOT, MIRROR
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("Usage: facts.py <bundle_root>")
    ROOT = os.path.abspath(sys.argv[1])
    MIRROR = find_mirror(ROOT)
    if MIRROR is None:
        sys.exit("facts.py: no install.ini found under the bundle (searched 6 levels deep)")
    for run in RUNNERS:
        run()
    print(json.dumps({"bundle_root": ROOT, "mirror": MIRROR, "facts": FACTS}, indent=2, default=str))


if __name__ == "__main__":
    main()
