"""Verdict rules for the platform, sizing and runtime checks (judgment only; see verdicts.py for the contract).

Each rule's text is the human-readable spec in `docs/verdict-rules.md` (keep the two in step). A fact that is missing from the bundle is
Needs Review, never an assumed Fail, except where the calibration says otherwise (SCALE-006)."""
from __future__ import annotations

import re

from verdicts import ABSENT, _missing, fact, rule, verdict


def _tier_target_gib(ram_gib: float) -> float:
    """The checklist's recommended cgroup memory cap for a host with `ram_gib` of RAM."""
    if ram_gib > 120:
        return 0.75 * ram_gib
    if ram_gib >= 60:
        return 0.66 * ram_gib
    if ram_gib >= 30:
        return ram_gib - 20
    return 0.5 * ram_gib


@rule("ARCH-001", "Separation of Design and Automation Nodes")
def design_automation_separation(facts):
    """Always Needs Review: a design bundle can't show an automation node, and an automation bundle can't show a design node."""
    node = fact(facts, "node")
    nodetype = node.get("nodetype", ABSENT) if isinstance(node, dict) else ABSENT
    if nodetype == ABSENT:
        return _missing("the node type")
    return verdict("Needs Review", f"a {nodetype} node bundle can't show whether the other node type exists or how projects are promoted", nodetype=nodetype)


@rule("SEC-004", "CGroups Enabled with Memory Limit per Sizing Heuristic")
def cgroups_memory_limit(facts):
    cg, host = fact(facts, "cgroups"), fact(facts, "host_memory")
    if not isinstance(cg, dict):
        return _missing("cgroup settings")
    enabled = cg.get("enabled", ABSENT)
    if enabled is False:
        return verdict("Fail", "cgroups are disabled", enabled=False)
    if enabled is not True:
        return _missing("the cgroups enabled flag")
    pcts = [lim["pct_of_MemTotal"] for lim in (cg.get("limits") if isinstance(cg.get("limits"), list) else [])
            if isinstance(lim, dict) and lim.get("pct_of_MemTotal") is not None]
    if not pcts:
        return verdict("Needs Review", "cgroups enabled but no memory limit set (ask whether intentional)", enabled=True)
    ram = host.get("GiB") if isinstance(host, dict) else None
    if not isinstance(ram, (int, float)) or ram <= 0:
        return _missing("host memory")
    pct = max(pcts)  # the overall memory cap if several are listed
    cap = pct / 100 * ram
    values = {"limit_pct_of_ram": pct, "ram_gib": ram, "limit_gib": round(cap, 1)}
    if pct >= 80:
        return verdict("Needs Review", f"limit is {pct}% of {ram} GiB: over-allocates memory to cgroups", **values)
    target = _tier_target_gib(ram)
    values["tier_target_gib"] = round(target, 1)
    if abs(cap - target) <= 0.10 * target:
        return verdict("Pass", f"limit {cap:.0f} GiB = {pct}% of {ram} GiB; within 10% of tier target {target:.0f} GiB", **values)
    return verdict("Needs Review", f"limit {cap:.0f} GiB = {pct}% of {ram} GiB; more than 10% from tier target {target:.0f} GiB", **values)


@rule("SCALE-001", "External PostgreSQL Runtime Database")
def external_postgresql(facts):
    db = fact(facts, "internal_database")
    if not isinstance(db, dict):
        return _missing("internal database settings")
    kind, loopback = db.get("type", ABSENT), db.get("host_is_loopback", ABSENT)
    values = {"type": kind, "host_is_loopback": loopback}
    if kind == ABSENT:
        return _missing("the internal database type")
    if str(kind).lower() != "postgresql":
        return verdict("Fail", f"internal database is {kind}, not PostgreSQL", **values)
    if loopback is True:
        return verdict("Pass", "PostgreSQL runtime database, locally installed on the DSS host (loopback)", **values)
    if loopback is False:
        return verdict("Pass", "PostgreSQL runtime database on a non-local host", **values)
    return _missing("the database host")


@rule("SCALE-006", "Usage of Instance Sanity Check")
def sanity_check_used(facts):
    sc = fact(facts, "sanity_check")
    if not isinstance(sc, dict):
        return verdict("Fail", "no sanity-check output in the bundle", present=False)
    if sc.get("empty") is True:
        return verdict("Fail", "sanity-check output is empty", present=True, messages=0)
    return verdict("Pass", f"sanity-check output present with {sc.get('messages')} message(s)", present=True, messages=sc.get("messages"))


_LIMITS = ("maxRunningJobs", "maxRunningActivities", "maxRunningActivitiesPerJob")


@rule("SCALE-009", "Flow Limits Sizing (Max Jobs, Max Activities)")
def flow_limits(facts):
    cl = fact(facts, "concurrency_limits")
    if not isinstance(cl, dict):
        return _missing("concurrency limits")
    values = {}
    for name in _LIMITS:
        found = cl.get(name)
        if not isinstance(found, list) or not found:
            return _missing(f"{name}")
        raw = found[0].get("value")  # first location listed; a limit in an unexpected place still counts
        values[name] = 0 if raw in (None, "") else raw  # blank means unsized, like 0
    if not all(isinstance(v, (int, float)) for v in values.values()):
        return _missing("numeric concurrency limits")
    zero = [n for n, v in values.items() if v == 0]
    if zero:
        return verdict("Fail", f"{', '.join(zero)} is 0 (unsized)", **values)
    if 30 <= values["maxRunningActivities"] <= 50 and values["maxRunningActivitiesPerJob"] == 5:
        return verdict("Pass", "limits set; activities within 30-50, per-job at 5", **values)
    return verdict("Needs Review", "limits set but outside the recommended ranges (ask whether justified)", **values)


@rule("SCALE-011", "Remove filesystem_root Connection")
def filesystem_root_removed(facts):
    conns = fact(facts, "connections")
    present = conns.get("filesystem_root_present", ABSENT) if isinstance(conns, dict) else ABSENT
    if present is True:
        return verdict("Fail", "filesystem_root connection still present", filesystem_root_present=True)
    if present is False:
        return verdict("Pass", "no filesystem_root connection", filesystem_root_present=False)
    return _missing("the connections list")


def _connection_tier(check_id_what, items, required, optional=()):
    """Status of a group of connections of one family. `required` components must be known (else Needs Review); `optional` ones count
    only when the reader found them. Every connection fully set = Pass, none set at all = Fail, anything between = Partial."""
    full = partial = 0
    for item in items:
        known = [item.get(c, ABSENT) for c in required]
        if any(not isinstance(v, bool) for v in known):
            return _missing(f"the {check_id_what} setting")
        known += [v for v in (item.get(c, ABSENT) for c in optional) if isinstance(v, bool)]
        if all(known):
            full += 1
        elif any(known):
            partial += 1
    values = {"connections": len(items), "fully_set": full, "partly_set": partial}
    if full == len(items):
        return verdict("Pass", f"all {len(items)} {check_id_what} connection(s) are set up", **values)
    if full == 0 and partial == 0:
        return verdict("Fail", f"none of the {len(items)} {check_id_what} connection(s) is set up", **values)
    return verdict("Partial", f"{full} of {len(items)} {check_id_what} connection(s) fully set up, {partial} partly", **values)


def _connection_family(facts, key, kinds, what, required, optional=()):
    conns = fact(facts, "connections")
    if not isinstance(conns, dict) or not isinstance(conns.get(key), list):
        return _missing("the connection settings")
    items = [c for c in conns[key] if isinstance(c, dict) and c.get("type") in kinds]
    if not items:
        return verdict("Not Applicable", f"no {what} connection is configured", connections=0)
    return _connection_tier(what, items, required, optional)


@rule("SCALE-012", "Cloud Object Storage Configuration (Details Readable By, HDFS Interface)")
def cloud_object_storage(facts):
    return _connection_family(facts, "cloud_storage", {"s3", "azure", "gcs"}, "cloud object storage", ("readable_by_set",), ("hdfs_interface_set",))


@rule("SCALE-013", "Snowflake Connection Configuration")
def snowflake_connections(facts):
    return _connection_family(facts, "warehouses", {"snowflake"}, "Snowflake", ("fast_write",), ("spark_native", "udf"))


@rule("SCALE-014", "Databricks Connection Configuration")
def databricks_connections(facts):
    return _connection_family(facts, "warehouses", {"databricks"}, "Databricks", ("fast_write",))


@rule("SCALE-015", "Amazon Redshift, Google BigQuery, Azure Synapse Connection Configuration")
def other_warehouse_connections(facts):
    return _connection_family(facts, "warehouses", {"redshift", "bigquery", "synapse"}, "Redshift, BigQuery or Synapse", ("fast_write",))


_DISK_FLAG_WORDS = ("rotational", "ssd", "hdd")


@rule("ARCH-004", "SSD Storage for DSS")
def ssd_storage(facts):
    """The disk facts and DSS's own sanity check, either of which can settle it. A sanity-check message about rotational
    disks is authoritative (Fail), even when the disks could not be read."""
    vol, sanity = fact(facts, "data_volume_device"), fact(facts, "sanity_check")
    messages = isinstance(sanity, dict) and sanity.get("empty") is False
    codes = sanity.get("codes") if messages else []
    if messages and not isinstance(codes, list):
        return None  # an older facts.py without message codes: the model reads the sanity-check text
    flagged = [c for c in codes if any(w in c.lower() for w in _DISK_FLAG_WORDS)]
    disks = vol.get("all_non_rotational") if isinstance(vol, dict) else None
    values = {"all_non_rotational": disks if isinstance(disks, bool) else ABSENT, "sanity_check_disk_codes": flagged}
    if flagged:
        return verdict("Fail", f"DSS's sanity check flags the disk type ({flagged[0]})", **values)
    if disks is False:
        return verdict("Fail", "a disk behind the data directory is rotational", **values)
    if disks is True:
        return verdict("Pass", "all disks behind the data directory are non-rotational", **values)
    return verdict("Needs Review", "the data directory's disks cannot be determined from the bundle", **values)


# --- Batch 4c: scale, connections, logs ----------------------------------------------------------------------------

_DEFAULT_STORAGE_FORMATS = "CSV_ESCAPING_NOGZIP_FORHIVE,CSV_EXCEL_GZIP,PARQUET_HIVE"  # the list DSS ships with: counts as blank
_CLEANUP_STEP = re.compile(r"clear|purge|delet|clean|remov|vacuum|prune", re.I)


@rule("SCALE-002", "Appropriate Metastore Configured")
def metastore_flavor(facts):
    m = fact(facts, "metastore_and_exports")
    flavor = m.get("metastore_flavor", ABSENT) if isinstance(m, dict) else ABSENT
    if flavor == ABSENT:
        return _missing("the metastore flavor")
    hadoop = m.get("hive_enabled") is True or m.get("hadoop_enabled_in_host_env") is True
    values = {"metastore_flavor": flavor, "hadoop_estate": hadoop}
    kind = flavor.upper()
    if "GLUE" in kind:
        return verdict("Needs Review", f"Glue metastore ({flavor}): proper AWS integration can't be verified from the bundle", **values)
    if "HIVE" in kind:
        if hadoop:
            return verdict("Pass", f"Hive metastore ({flavor}) on a Hadoop estate", **values)
        return verdict("Needs Review", f"Hive metastore ({flavor}) but no Hadoop estate is visible", **values)
    if "INTERNAL" in kind:
        if hadoop:
            return verdict("Needs Review", f"DSS internal metastore ({flavor}) on a Hadoop estate where Hive may fit", **values)
        return verdict("Pass", f"DSS internal metastore ({flavor}), no Hadoop estate", **values)
    return verdict("Needs Review", f"unrecognised metastore flavor {flavor}", **values)


@rule("SCALE-003", "Graphics Export (PDF/Image) Configuration")
def graphics_export(facts):
    m = fact(facts, "metastore_and_exports")
    on = m.get("graphics_exports_enabled", ABSENT) if isinstance(m, dict) else ABSENT
    if on is True:
        return verdict("Pass", "graphics export is enabled", graphics_exports_enabled=True)
    if on is False:
        return verdict("Needs Review", "graphics export is off (ask whether intentional)", graphics_exports_enabled=False)
    return _missing("the graphics export setting")


@rule("SCALE-004", "Admin Project for Garbage Collection")
def admin_cleanup_project(facts):
    a = fact(facts, "admin_cleanup_scenarios")
    if not isinstance(a, dict) or not isinstance(a.get("candidate_projects"), dict):
        return _missing("the project list")
    projects = a["candidate_projects"]
    if not projects:
        return verdict("Fail", "no admin or maintenance project found", candidate_projects=0)
    scenarios = [(key, sc) for key, lst in projects.items() for sc in lst if isinstance(sc, dict) and "error" not in sc]
    scheduled = [(k, sc) for k, sc in scenarios
                 if sc.get("active") is True and any(t.get("active") is True and t.get("type") == "temporal" for t in sc.get("triggers") or [])]
    values = {"candidate_projects": sorted(projects), "scenarios": len(scenarios), "active_scheduled": len(scheduled)}
    clean = [(k, sc) for k, sc in scheduled
             if sc.get("scripted") is False and any(_CLEANUP_STEP.search(str(n)) for n in sc.get("step_names") or [])]
    if clean:
        k, sc = clean[0]
        return verdict("Pass", f"{k}: active scheduled step-based scenario {sc.get('file')} with cleanup steps", **values)
    if scheduled:
        return verdict("Needs Review", "an active scheduled scenario exists but its cleanup purpose is not clear from its steps (a script is never read)", **values)
    if any(sc.get("active") is True for _, sc in scenarios):
        return verdict("Needs Review", "a candidate project has active scenarios but none is scheduled", **values)
    return verdict("Fail", "candidate project(s) have no active scenario", **values)


@rule("SCALE-007", "Backend.log Error Review")
def backend_log_errors(facts):
    log = fact(facts, "backend_log")
    if not isinstance(log, dict):
        return _missing("the backend logs")
    counts = {k: log.get(k, 0) for k in ("ERROR", "FATAL", "WARN")}
    values = {**counts, "files": len(log.get("files") or [])}
    if sum(counts.values()) > 0:
        return verdict("Needs Review", f"backend logs hold {counts['ERROR']} ERROR, {counts['FATAL']} FATAL, {counts['WARN']} WARN entries", **values)
    return verdict("Pass", "no ERROR, FATAL or WARN entries in the backend logs", **values)


def _gib(text):
    """A JVM heap size such as 12g, 8192m, 1t as GiB, or None."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgt]?)b?\s*", str(text).lower())
    if not m:
        return None
    return float(m.group(1)) * {"": 1 / 2 ** 30, "k": 1 / 2 ** 20, "m": 1 / 1024, "g": 1, "t": 1024}[m.group(2)]


def _backend_tier_gib(ram_gib):
    """The checklist's minimum backend heap for a host with `ram_gib` of RAM (None below the first tier)."""
    for floor, xmx in ((95, 16), (30, 8), (12, 4)):
        if ram_gib > floor:
            return xmx
    return None


@rule("SCALE-008", "Backend Xmx Sizing")
def backend_xmx(facts):
    heaps, host = fact(facts, "heap_sizes"), fact(facts, "host_memory")
    raw = heaps.get("javaopts.backend.xmx") if isinstance(heaps, dict) else None
    xmx = _gib(raw) if raw else None
    if xmx is None:
        return _missing("backend.xmx")
    cfg = fact(facts, "config_folder_size")
    cfg_gib = cfg.get("GiB") if isinstance(cfg, dict) else None
    ram = host.get("GiB") if isinstance(host, dict) else None
    log = fact(facts, "backend_log")
    ooms = log.get("OutOfMemoryError") if isinstance(log, dict) else None
    values = {"backend_xmx": raw, "ram_gib": ram if isinstance(ram, (int, float)) else ABSENT,
              "config_folder_gib": cfg_gib if isinstance(cfg_gib, (int, float)) else ABSENT,
              "outofmemory_mentions": ooms if isinstance(ooms, int) else ABSENT}
    misses, unknown = [], []
    if isinstance(ram, (int, float)) and ram > 0:
        tier = _backend_tier_gib(ram)
        if tier and xmx < tier:
            misses.append(f"{raw} is below the {tier}g tier for {ram} GiB of RAM")
    else:
        unknown.append("host memory")
    if 32 <= xmx < 48:
        misses.append(f"{raw} sits in the 32-48 GB dead zone")
    if isinstance(cfg_gib, (int, float)) and cfg_gib > 0:
        if xmx < 3 * cfg_gib:
            misses.append(f"{raw} is under 3x the {cfg_gib} GiB config folder")
    else:
        unknown.append("config folder size")
    if isinstance(ooms, int):
        if ooms > 0:
            misses.append(f"{ooms} OutOfMemoryError mention(s) in the backend logs")
    else:
        unknown.append("backend logs")
    if misses:
        return verdict("Fail", "; ".join(misses), **values)
    if unknown:
        return verdict("Needs Review", f"no sizing rule missed, but {', '.join(unknown)} missing from the bundle", **values)
    return verdict("Pass", f"backend.xmx {raw} meets the tier, 3x config and dead-zone rules; no OutOfMemoryError in the logs", **values)


@rule("SCALE-010", "Preferred Connections and Engines Settings")
def preferred_connections_and_engines(facts):
    prefs = fact(facts, "default_preferences")
    if not isinstance(prefs, dict):
        return _missing("the default dataset-creation settings")
    ds = prefs.get("defaultDatasetCreationSettings")
    ds = ds if isinstance(ds, dict) else {}
    engines = prefs.get("recipeEnginesPreferences_nonempty")
    engines = engines if isinstance(engines, dict) else {}
    set_values = {k: v for k, v in ds.items() if v not in (ABSENT, "", None) and not (k == "preferedStorageFormats" and v == _DEFAULT_STORAGE_FORMATS)}
    if set_values or engines:
        names = sorted([*set_values, *engines])
        return verdict("Needs Review", f"non-blank preference(s): {', '.join(names)} (ask whether a use case justifies them)",
                       **{**set_values, **{f"engine:{k}": v for k, v in engines.items()}})
    return verdict("Pass", "default connection, upload connection and engine preferences are blank; storage formats are blank or the DSS default list")
