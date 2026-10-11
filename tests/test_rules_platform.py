"""The platform/sizing verdict rules (scripts/rules_platform.py): edge cases on hand-built facts and agreement with the
fixtures' expected answers."""
import json
import subprocess
import sys

import pytest
import yaml

from conftest import FIXTURES, REPO_ROOT

SCRIPTS = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts"
FACTS_PY = REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "facts.py"
sys.path.insert(0, str(SCRIPTS))
import rules_platform  # noqa: E402,F401
import verdicts  # noqa: E402

RULED = {"ARCH-001", "SEC-004", "SCALE-001", "SCALE-006", "SCALE-009", "SCALE-011", "ARCH-004",
         "SCALE-002", "SCALE-003", "SCALE-012", "SCALE-013", "SCALE-014", "SCALE-015", "SCALE-004", "SCALE-007", "SCALE-008", "SCALE-010"}


def facts(**blocks):
    return {"facts": {name: {"value": value, "source": "test"} for name, value in blocks.items()}}


def run(check_id, doc):
    anchor = verdicts.RULES[check_id][0]
    out = verdicts.compute(doc, [{"id": check_id, "title": anchor}])
    return out["verdicts"][0]["status"] if out["verdicts"] else "undecided"


def cg(pct, enabled=True):
    return {"enabled": enabled, "limits": [{"cgroup": "memory/DSS", "value": "x", "pct_of_MemTotal": pct}] if pct is not None else "ABSENT"}


def host(gib):
    return {"GiB": gib, "MemTotal_kB": int(gib * 1048576)}


def limits(jobs=5, acts=40, per=5):
    wrap = lambda v: [{"path": "p", "value": v}]
    return {"maxRunningJobs": wrap(jobs), "maxRunningActivities": wrap(acts), "maxRunningActivitiesPerJob": wrap(per)}


def test_the_platform_rules_are_registered():
    assert RULED <= set(verdicts.RULES)


@pytest.mark.parametrize("ram,tier_pct", [(250, 75), (120, 66), (62.5, 66), (60, 66), (45, None), (30, None), (16, 50)])
def test_sec004_tier_targets(ram, tier_pct):
    """Pass exactly at the tier target; the target is 75% over 120 GiB, 66% for 60-120, RAM-20 for 30-60, 50% below 30."""
    target = {250: 0.75 * 250, 120: 0.66 * 120, 62.5: 0.66 * 62.5, 60: 0.66 * 60, 45: 25, 30: 10, 16: 8}[ram]
    assert run("SEC-004", facts(cgroups=cg(round(target / ram * 100, 1)), host_memory=host(ram))) == "Pass"


@pytest.mark.parametrize("pct,expected", [
    (66.0, "Pass"), (72.0, "Pass"),            # 9% above a 66% target (62.5 GiB host: 41.25 GiB)
    (74.0, "Needs Review"), (55.0, "Needs Review"),   # more than 10% away either side
    (80.0, "Needs Review"), (95.0, "Needs Review"),   # 80% or more is checked first
])
def test_sec004_band_and_the_80_percent_override(pct, expected):
    assert run("SEC-004", facts(cgroups=cg(pct), host_memory=host(62.5))) == expected


@pytest.mark.parametrize("doc,expected", [
    (facts(cgroups=cg(None, enabled=False), host_memory=host(62.5)), "Fail"),
    (facts(cgroups=cg(None), host_memory=host(62.5)), "Needs Review"),         # enabled, no memory limit
    (facts(cgroups="ABSENT", host_memory=host(62.5)), "Needs Review"),
    (facts(cgroups={"enabled": "ABSENT"}, host_memory=host(62.5)), "Needs Review"),
    (facts(cgroups=cg(66.0), host_memory="ABSENT"), "Needs Review"),
])
def test_sec004_disabled_missing_and_unlimited(doc, expected):
    assert run("SEC-004", doc) == expected


def test_sec004_uses_the_largest_memory_limit_when_several_are_listed():
    two = {"enabled": True, "limits": [{"pct_of_MemTotal": 10.0}, {"pct_of_MemTotal": 66.0}, {"pct_of_MemTotal": None}]}
    assert run("SEC-004", facts(cgroups=two, host_memory=host(62.5))) == "Pass"


@pytest.mark.parametrize("db,expected", [
    ({"type": "PostgreSQL", "host_is_loopback": False}, "Pass"),
    ({"type": "postgresql", "host_is_loopback": True}, "Pass"),   # locally installed: Pass, with a comment
    ({"type": "H2", "host_is_loopback": "ABSENT"}, "Fail"),
    ({"type": "ABSENT", "host_is_loopback": "ABSENT"}, "Needs Review"),
    ({"type": "PostgreSQL", "host_is_loopback": "ABSENT"}, "Needs Review"),
    ("ABSENT", "Needs Review"),
])
def test_scale001_database(db, expected):
    assert run("SCALE-001", facts(internal_database=db)) == expected


def test_scale001_names_the_missing_override_not_missing_settings():
    def reason(searched):
        doc = {"facts": {"internal_database": {"value": "ABSENT", "searched": searched}}}
        return verdicts.compute(doc, [{"id": "SCALE-001", "title": verdicts.RULES["SCALE-001"][0]}])["verdicts"][0]["reason"]
    assert "embedded H2" in reason(["config/general-settings.json: internalDatabase.connection"])
    assert reason(["config/general-settings.json"]) == "internal database settings missing from the bundle"


@pytest.mark.parametrize("sc,expected", [
    ({"present": True, "empty": False, "messages": 3}, "Pass"),
    ({"present": True, "empty": True, "messages": 0}, "Fail"),
    ("ABSENT", "Fail"),       # a missing sanity check is a Fail here, per the calibration; never Partial or Needs Review
])
def test_scale006_presence_only(sc, expected):
    assert run("SCALE-006", facts(sanity_check=sc)) == expected


@pytest.mark.parametrize("lim,expected", [
    (limits(5, 40, 5), "Pass"),
    (limits(5, 30, 5), "Pass"), (limits(5, 50, 5), "Pass"),
    (limits(0, 40, 5), "Fail"), (limits(5, 0, 5), "Fail"), (limits(5, 40, 0), "Fail"),
    (limits(None, 40, 5), "Fail"),                   # blank means unsized
    (limits(0, 0, 0), "Fail"),
    (limits(5, 10, 5), "Needs Review"), (limits(5, 60, 5), "Needs Review"), (limits(5, 40, 4), "Needs Review"),
])
def test_scale009_flow_limits(lim, expected):
    assert run("SCALE-009", facts(concurrency_limits=lim)) == expected


def test_scale009_a_missing_limit_is_needs_review_and_a_limit_in_another_place_still_counts():
    partial = limits()
    partial["maxRunningJobs"] = "ABSENT"
    assert run("SCALE-009", facts(concurrency_limits=partial)) == "Needs Review"
    assert run("SCALE-009", facts(concurrency_limits="ABSENT")) == "Needs Review"
    moved = limits(0, 40, 5)
    moved["maxRunningJobs"] = [{"path": "jekSettings.maxRunningJobs", "value": 0}]
    assert run("SCALE-009", facts(concurrency_limits=moved)) == "Fail"


@pytest.mark.parametrize("conns,expected", [
    ({"filesystem_root_present": True}, "Fail"), ({"filesystem_root_present": False}, "Pass"),
    ({"filesystem_root_present": "ABSENT"}, "Needs Review"), ("ABSENT", "Needs Review"),
])
def test_scale011_filesystem_root(conns, expected):
    assert run("SCALE-011", facts(connections=conns)) == expected


SSD, HDD = {"all_non_rotational": True}, {"all_non_rotational": False}
QUIET = {"empty": True, "messages": 0, "codes": []}
WARN_OTHER = {"empty": False, "messages": 4, "codes": ["WARN_PROJECT_LARGE_JOB_HISTORY", "WARN_MISC_CODE_ENV_USES_PYSPARK"]}
WARN_DISK = {"empty": False, "messages": 2, "codes": ["WARN_MISC_DATADIR_ON_ROTATIONAL_DISK", "WARN_SECURITY_NO_CGROUPS"]}
WARN_OLD = {"empty": False, "messages": 2}   # a facts.py without message codes


@pytest.mark.parametrize("vol,sanity,expected", [
    (SSD, QUIET, "Pass"), (SSD, "ABSENT", "Pass"),
    (SSD, WARN_OTHER, "Pass"),                 # sanity messages about other things do not block a Pass
    (SSD, WARN_DISK, "Fail"),                  # DSS's own sanity check is authoritative
    (HDD, QUIET, "Fail"), (HDD, WARN_OTHER, "Fail"),
    ("ABSENT", WARN_DISK, "Fail"),             # flagged even when lsblk could not be read
    ("ABSENT", WARN_OTHER, "Needs Review"), ("ABSENT", QUIET, "Needs Review"), ("ABSENT", "ABSENT", "Needs Review"),
    ({"backing_disks": []}, QUIET, "Needs Review"),
    (SSD, WARN_OLD, "undecided"), ("ABSENT", WARN_OLD, "undecided"),   # older facts: the model reads the sanity-check text
])
def test_arch004_disks_and_sanity_check(vol, sanity, expected):
    assert run("ARCH-004", facts(data_volume_device=vol, sanity_check=sanity)) == expected


def test_arch004_reason_names_the_flagging_code_and_matches_case_insensitively():
    doc = facts(data_volume_device=SSD, sanity_check={"empty": False, "messages": 1, "codes": ["warn_datadir_on_Rotational_disk"]})
    out = verdicts.compute(doc, [{"id": "ARCH-004", "title": "SSD Storage for DSS"}])["verdicts"][0]
    assert out["status"] == "Fail" and "warn_datadir_on_Rotational_disk" in out["reason"]


def test_scale001_loopback_reason_says_it_is_installed_locally():
    out = verdicts.compute(facts(internal_database={"type": "PostgreSQL", "host_is_loopback": True}),
                           [{"id": "SCALE-001", "title": verdicts.RULES["SCALE-001"][0]}])["verdicts"][0]
    assert out["status"] == "Pass" and "locally installed" in out["reason"]


def test_an_undecided_row_is_listed_and_gets_no_verdict():
    doc = verdicts.compute(facts(data_volume_device="ABSENT", sanity_check=WARN_OLD), [{"id": "ARCH-004", "title": "SSD Storage for DSS"}])
    assert doc["verdicts"] == [] and doc["undecided"] == [{"id": "ARCH-004", "title": "SSD Storage for DSS"}]


@pytest.mark.parametrize("scenario", sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml")))
def test_platform_rules_agree_with_the_fixtures_expected_answers(scenario):
    proc = subprocess.run([sys.executable, "-B", str(FACTS_PY), str(FIXTURES / "bundles" / scenario)], capture_output=True, text=True, check=True)
    expected = yaml.safe_load((FIXTURES / "expected" / f"{scenario}.yaml").read_text())["items"]
    rows = [{"id": i, "title": verdicts.RULES[i][0]} for i in RULED]
    doc = verdicts.compute(json.loads(proc.stdout), rows)
    decided = {v["id"]: v["status"] for v in doc["verdicts"]}
    assert len(decided) + len(doc["undecided"]) == len(RULED)
    for check_id, status in decided.items():
        if check_id in expected:
            assert status in expected[check_id]["status"], f"{scenario} {check_id}: verdict {status}, expected {expected[check_id]['status']}"


# --- Batch 4c: metastore, graphics export, admin cleanup, backend log, Xmx, preferences -------------------------------

def meta(flavor="HIVESERVER2", hive=True, hadoop="ABSENT", graphics=True):
    return {"metastore_flavor": flavor, "hive_enabled": hive, "hadoop_enabled_in_host_env": hadoop, "graphics_exports_enabled": graphics}


@pytest.mark.parametrize("m,expected", [
    (meta(), "Pass"),
    (meta(hive="ABSENT", hadoop=True), "Pass"),
    (meta(hive=False), "Needs Review"),
    (meta("DSS_INTERNAL", hive="ABSENT"), "Pass"),
    (meta("DSS_INTERNAL", hive=True), "Needs Review"),
    (meta("GLUE"), "Needs Review"),
    (meta("SOMETHING_ELSE"), "Needs Review"),
    (meta("ABSENT"), "Needs Review"),
    ("ABSENT", "Needs Review"),
])
def test_scale002_metastore_matches_the_estate(m, expected):
    assert run("SCALE-002", facts(metastore_and_exports=m)) == expected


@pytest.mark.parametrize("graphics,expected", [(True, "Pass"), (False, "Needs Review"), ("ABSENT", "Needs Review")])
def test_scale003_graphics_export(graphics, expected):
    assert run("SCALE-003", facts(metastore_and_exports=meta(graphics=graphics))) == expected


def sc(steps=("Clear Job logs",), active=True, scheduled=True, scripted=False):
    return {"file": "S.json", "scripted": scripted, "active": active, "step_names": list(steps),
            "triggers": [{"type": "temporal", "active": scheduled}] if scheduled is not None else []}


@pytest.mark.parametrize("projects,expected", [
    ({"ADMINPROJECT": [sc()]}, "Pass"),
    ({"ADMINPROJECT": [sc(("Purge old data",))]}, "Pass"),
    ({}, "Fail"),
    ({"ADMINPROJECT": []}, "Fail"),
    ({"ADMINPROJECT": [sc(active=False)]}, "Fail"),
    ({"ADMINPROJECT": [sc(scripted=True, steps=())]}, "Needs Review"),
    ({"ADMINPROJECT": [sc(steps=("build dataset",))]}, "Needs Review"),
    ({"ADMINPROJECT": [sc(scheduled=False)]}, "Needs Review"),
    ({"ADMINPROJECT": [sc(scheduled=None)]}, "Needs Review"),
    ({"ADMINPROJECT": [sc(scripted=True, steps=()), sc()]}, "Pass"),
])
def test_scale004_admin_cleanup(projects, expected):
    assert run("SCALE-004", facts(admin_cleanup_scenarios={"candidate_projects": projects, "candidate_count": len(projects)})) == expected


def test_scale004_missing_project_list_is_needs_review():
    assert run("SCALE-004", facts(admin_cleanup_scenarios="ABSENT")) == "Needs Review"


def blog(error=0, fatal=0, warn=0, oom=0):
    return {"files": [{"file": "backend.log"}], "ERROR": error, "FATAL": fatal, "WARN": warn, "OutOfMemoryError": oom}


@pytest.mark.parametrize("log,expected", [
    (blog(), "Pass"), (blog(error=1), "Needs Review"), (blog(warn=1), "Needs Review"), (blog(fatal=1), "Needs Review"),
    ("ABSENT", "Needs Review"),
])
def test_scale007_backend_log_errors_are_needs_review_never_fail(log, expected):
    assert run("SCALE-007", facts(backend_log=log)) == expected


def xmx_facts(xmx="16g", ram=250, cfg=1.0, oom=0):
    kw = {"heap_sizes": {"javaopts.backend.xmx": xmx}}
    if ram is not None:
        kw["host_memory"] = host(ram)
    if cfg is not None:
        kw["config_folder_size"] = {"GiB": cfg}
    if oom is not None:
        kw["backend_log"] = blog(oom=oom)
    return facts(**kw)


@pytest.mark.parametrize("kw,expected", [
    ({}, "Pass"),
    ({"xmx": "12g"}, "Fail"),                      # below the 16g tier for >95 GiB
    ({"xmx": "8g", "ram": 62.5}, "Pass"),          # 8g tier
    ({"xmx": "4g", "ram": 62.5}, "Fail"),
    ({"xmx": "4g", "ram": 16}, "Pass"),            # 4g tier above 12 GiB
    ({"xmx": "2g", "ram": 8, "cfg": 0.5}, "Pass"),             # no tier below 12 GiB
    ({"xmx": "40g"}, "Fail"),                      # the 32-48 GB dead zone
    ({"xmx": "48g"}, "Pass"),
    ({"xmx": "8192m", "ram": 62.5}, "Pass"),
    ({"cfg": 6.0}, "Fail"),                        # 16g < 3 x 6
    ({"cfg": 5.0}, "Pass"),                        # exactly 3x passes
    ({"oom": 2}, "Fail"),
    ({"cfg": None}, "Needs Review"),               # nothing missed, config size absent
    ({"oom": None}, "Needs Review"),
    ({"ram": None}, "Needs Review"),
    ({"cfg": None, "xmx": "12g"}, "Fail"),         # a confirmed miss wins over a missing input
    ({"cfg": None, "oom": 1}, "Fail"),
])
def test_scale008_backend_xmx(kw, expected):
    assert run("SCALE-008", xmx_facts(**kw)) == expected


def test_scale008_missing_xmx_is_needs_review():
    assert run("SCALE-008", facts(heap_sizes="ABSENT", host_memory=host(64))) == "Needs Review"


def prefs(**ds):
    base = {"preferedConnection": "ABSENT", "forcedPreferedConnection": "ABSENT", "preferedUploadConnection": "ABSENT",
            "preferedStorageFormats": "ABSENT"}
    return {"defaultDatasetCreationSettings": {**base, **ds}, "recipeEnginesPreferences_nonempty": {}}


@pytest.mark.parametrize("p,expected", [
    (prefs(), "Pass"),
    (prefs(preferedStorageFormats="CSV_ESCAPING_NOGZIP_FORHIVE,CSV_EXCEL_GZIP,PARQUET_HIVE"), "Pass"),  # DSS's own default list
    (prefs(preferedStorageFormats="PARQUET_HIVE"), "Needs Review"),
    (prefs(preferedUploadConnection="filesystem_managed"), "Needs Review"),
    (prefs(forcedPreferedConnection="local"), "Needs Review"),
    ({**prefs(), "recipeEnginesPreferences_nonempty": {"enginesPreferenceOrder": ["SPARK"]}}, "Needs Review"),
    ("ABSENT", "Needs Review"),
])
def test_scale010_preferences(p, expected):
    assert run("SCALE-010", facts(default_preferences=p)) == expected


@pytest.mark.parametrize("nodetype", ["design", "automation", "deployer", "api"])
def test_arch001_is_needs_review_for_every_node_type(nodetype):
    doc = facts(node={"nodetype": nodetype, "nodeid": "n", "installid": "i", "product_version": "14.0.0"})
    assert run("ARCH-001", doc) == "Needs Review"
    v = verdicts.compute(doc, [{"id": "ARCH-001", "title": verdicts.RULES["ARCH-001"][0]}])["verdicts"][0]
    assert v["deciding_values"] == {"nodetype": nodetype}


def test_arch001_missing_node_type_is_needs_review():
    assert run("ARCH-001", facts(node={"nodetype": "ABSENT"})) == "Needs Review"
    assert run("ARCH-001", facts()) == "Needs Review"


def stor(readable=True, hdfs=True, kind="gcs"):
    return {"type": kind, "readable_by_set": readable, "hdfs_interface_set": hdfs}


def wh(kind, fast=True, spark="ABSENT", udf="ABSENT"):
    return {"type": kind, "fast_write": fast, "spark_native": spark, "udf": udf}


def conns(cloud=(), warehouses=()):
    return facts(connections={"count": 1, "filesystem_root_present": False, "cloud_storage": list(cloud), "warehouses": list(warehouses)})


@pytest.mark.parametrize("cloud,expected", [
    ([], "Not Applicable"),
    ([stor()], "Pass"),
    ([stor(), stor(kind="s3")], "Pass"),
    ([stor(hdfs="ABSENT")], "Pass"),                        # S3-style connection without the HDFS interface setting
    ([stor(hdfs=False)], "Partial"),
    ([stor(), stor(readable=False, hdfs=False)], "Partial"),
    ([stor(readable=False, hdfs=False)], "Fail"),
    ([stor(readable="ABSENT")], "Needs Review"),
])
def test_scale012_cloud_object_storage(cloud, expected):
    assert run("SCALE-012", conns(cloud=cloud)) == expected


@pytest.mark.parametrize("check_id,kind", [("SCALE-013", "snowflake"), ("SCALE-014", "databricks"), ("SCALE-015", "redshift"),
                                           ("SCALE-015", "bigquery"), ("SCALE-015", "synapse")])
def test_warehouse_fast_write(check_id, kind):
    assert run(check_id, conns(warehouses=[])) == "Not Applicable"
    assert run(check_id, conns(warehouses=[wh(kind)])) == "Pass"
    assert run(check_id, conns(warehouses=[wh(kind), wh(kind, fast=False)])) == "Partial"
    assert run(check_id, conns(warehouses=[wh(kind, fast=False)])) == "Fail"
    assert run(check_id, conns(warehouses=[wh(kind, fast="ABSENT")])) == "Needs Review"


def test_scale013_spark_native_and_udf_count_only_when_found():
    assert run("SCALE-013", conns(warehouses=[wh("snowflake", spark=True, udf=True)])) == "Pass"
    assert run("SCALE-013", conns(warehouses=[wh("snowflake", spark=False)])) == "Partial"
    assert run("SCALE-013", conns(warehouses=[wh("snowflake", fast=False, spark=False, udf=False)])) == "Fail"


def test_warehouse_families_do_not_mix():
    doc = conns(warehouses=[wh("snowflake", fast=False)])
    assert run("SCALE-014", doc) == "Not Applicable" and run("SCALE-015", doc) == "Not Applicable"


@pytest.mark.parametrize("check_id", ["SCALE-012", "SCALE-013", "SCALE-014", "SCALE-015"])
def test_older_facts_without_connection_details_need_review(check_id):
    assert run(check_id, facts(connections={"count": 3, "filesystem_root_present": False})) == "Needs Review"
    assert run(check_id, facts()) == "Needs Review"
