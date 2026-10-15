"""The reader's facts.py reports key settings deterministically and never leaks secrets.

Runs it on the synthetic fixture bundles only (never a real bundle). A value mis-stated or
missed by hand is what made repeat reviews disagree, so these pin the contract: explicit
ABSENT, leaf-key search finds a limit under jekSettings, loopback detection, no secret values."""

import functools
import json
import shutil
import subprocess
import sys

import pytest

from conftest import FIXTURES, REPO_ROOT

FACTS = REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "facts.py"
BUNDLES = FIXTURES / "bundles"


def _run(bundle_dir):
    proc = subprocess.run([sys.executable, "-B", str(FACTS), str(bundle_dir)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


@functools.lru_cache(maxsize=None)
def _fixture_facts(bundle):
    """The fixture bundles are read-only, so one run per bundle serves every test."""
    return json.loads(_run(BUNDLES / bundle))["facts"]


def run_facts(bundle):
    return _fixture_facts(bundle)


def mutated_bundle(tmp_path, src, edit):
    """Copy a fixture bundle and apply edit(general_settings_dict); return the new bundle dir."""
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLES / src, bundle)
    settings = next(bundle.rglob("general-settings.json"))
    doc = json.loads(settings.read_text())
    edit(doc)
    settings.write_text(json.dumps(doc))
    return bundle


def test_loopback_database_and_limit_under_jek_settings():
    facts = run_facts("synthetic_design_baseline")
    db = facts["internal_database"]["value"]
    assert db["type"] == "PostgreSQL" and db["host"] == "127.0.0.1" and db["host_is_loopback"] is True
    jobs = facts["concurrency_limits"]["value"]["maxRunningJobs"]
    assert jobs == [{"path": "jekSettings.maxRunningJobs", "value": 0}]


def test_remote_database_is_not_loopback_and_agent_hub_is_detected():
    facts = run_facts("synthetic_design_k8s_remote")
    assert facts["internal_database"]["value"]["host_is_loopback"] is False
    assert facts["plugins"]["value"]["agent_hub_installed"] is True
    assert facts["connections"]["value"]["filesystem_root_present"] is False


def test_missing_settings_are_explicit_absent_never_false_or_zero():
    facts = run_facts("synthetic_design_baseline")
    assert facts["config_folder_size"]["value"] == "ABSENT"
    assert facts["trace_explorer"]["value"] == "ABSENT"
    assert facts["sso_and_ldap"]["value"]["ssoSettings.enabled"] == "ABSENT"


def test_absent_marker_is_not_masked_by_secret_key_redaction(tmp_path):
    """A missing key whose name looks secret-ish ("authenticationEnabled") must still read ABSENT."""
    bundle = mutated_bundle(tmp_path, "synthetic_design_baseline", lambda doc: doc.pop("ldapSettings"))
    facts = json.loads(_run(bundle))["facts"]
    assert facts["sso_and_ldap"]["value"]["ldapSettings.authenticationEnabled"] == "ABSENT"


def test_cgroup_limit_is_reported_as_a_percentage_of_host_memory():
    cg = run_facts("synthetic_design_k8s_remote")["cgroups"]["value"]
    assert cg["enabled"] is True
    limit = cg["limits"][0]
    assert limit["value"] == "42G" and limit["pct_of_MemTotal"] == pytest.approx(67.2, abs=0.2)


@pytest.mark.parametrize("bundle", sorted(p.name for p in BUNDLES.iterdir() if p.is_dir()))
def test_no_fact_errors(bundle):
    facts = run_facts(bundle)
    assert all(f["value"] != "ERROR" for f in facts.values()), facts


def test_plaintext_database_password_is_flagged_but_never_printed(tmp_path):
    secret = "Sup3r-S3cret-Value"
    bundle = mutated_bundle(tmp_path, "synthetic_design_baseline",
                            lambda doc: doc["internalDatabase"]["connection"].setdefault("params", {}).update(password=secret))
    out = _run(bundle)
    assert secret not in out
    assert json.loads(out)["facts"]["internal_database"]["value"]["password_stored_in_plaintext"] is True


def _facts_for(bundle_dir):
    out = _run(bundle_dir)
    return out, json.loads(out)["facts"]


def test_data_volume_device_follows_the_data_dir_to_its_disk_rota():
    vol = run_facts("synthetic_design_k8s_remote")["data_volume_device"]["value"]
    assert vol["mount_point"] == "/data/dataiku"
    assert vol["backing_disks"] == [{"disk": "sda", "rota": 0}] and vol["all_non_rotational"] is True
    assert run_facts("synthetic_design_baseline")["data_volume_device"]["value"] == "ABSENT"


def test_data_volume_device_reports_a_rotational_disk(tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLES / "synthetic_design_k8s_remote", bundle)
    diag = bundle / "diag.txt"
    diag.write_text(diag.read_text().replace("512    0 ", "512    1 "))
    _, facts = _facts_for(bundle)
    vol = facts["data_volume_device"]["value"]
    assert vol["backing_disks"] == [{"disk": "sda", "rota": 1}] and vol["all_non_rotational"] is False


def test_admin_cleanup_scenarios_summarise_type_activity_and_triggers_without_reading_scripts():
    healthy = run_facts("synthetic_design_k8s_remote")["admin_cleanup_scenarios"]["value"]["candidate_projects"]
    assert healthy["ADMINPROJECT"][0]["type"] == "step_based" and healthy["ADMINPROJECT"][0]["active"] is True
    assert healthy["ADMINPROJECT"][0]["triggers"] == [{"type": "temporal", "active": True}]
    py = run_facts("synthetic_design_admin_python")["admin_cleanup_scenarios"]["value"]["candidate_projects"]
    assert [s["file"] for s in py["ADMINISTRATIONPROJECT"]] == ["NIGHTLY_TASKS.json"]  # the .py is never listed or read
    assert py["ADMINISTRATIONPROJECT"][0]["type"] == "custom_python"


def test_deployer_reports_target_host_and_never_the_api_key(tmp_path):
    key = "Zk9-deployer-API-key-value"
    bundle = mutated_bundle(tmp_path, "synthetic_design_k8s_remote", lambda doc: doc["deployerClientSettings"].update(
        apiKey=key, nodeUrl="https://user:pw@deployer.synthetic.example:11200/x"))
    out, facts = _facts_for(bundle)
    dep = facts["deployer"]["value"]
    assert dep["mode"] == "REMOTE" and dep["target_host"] == "deployer.synthetic.example:11200"
    assert dep["api_key_configured"] is True
    assert key not in out and "user:pw" not in out


def test_ldap_authorized_groups_are_counted_not_named():
    assert run_facts("synthetic_design_baseline")["sso_and_ldap"]["value"]["ldapSettings.authorizedGroups_count"] == 0
    stdout = _run(BUNDLES / "synthetic_design_k8s_remote")
    assert json.loads(stdout)["facts"]["sso_and_ldap"]["value"]["ldapSettings.authorizedGroups_count"] == 2
    assert "dss-users" not in stdout


def test_missing_install_id_is_absent():
    assert run_facts("synthetic_design_admin_python")["node"]["value"]["installid"] == "ABSENT"
    assert run_facts("synthetic_design_baseline")["node"]["value"]["installid"] == "SYNTHETICINSTALL01"


def test_sanity_check_reports_presence_and_counts_or_absent():
    assert run_facts("synthetic_design_baseline")["sanity_check"]["value"]["present"] is True
    assert run_facts("synthetic_design_baseline")["sanity_check"]["value"]["empty"] is False
    assert run_facts("synthetic_design_k8s_remote")["sanity_check"]["value"]["empty"] is True  # {"messages": []}
    assert run_facts("synthetic_design_admin_python")["sanity_check"]["value"] == "ABSENT"


def test_byo_llm_is_active_only_when_a_main_llm_or_reference_project_is_set():
    assert run_facts("synthetic_design_baseline")["byo_llm"]["value"] == "ABSENT"  # no localAIServerSettings block
    on = run_facts("synthetic_design_k8s_remote")["byo_llm"]["value"]
    assert on["active"] is True and on["referenceProjectKey_set"] is True and on["mainLLMId"].endswith("gpt-5.2")
    partial = run_facts("synthetic_design_admin_python")["byo_llm"]["value"]
    assert partial["active"] is True and partial["referenceProjectKey_set"] is False


def test_backend_log_groups_error_patterns_and_run_as_errors_without_user_names(tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLES / "synthetic_design_baseline", bundle)
    log = next(bundle.rglob("backend.log"))
    metric = "[2026/01/06-0{h}:00:00.000] [m-{h}] [ERROR] [dku.monitoring] - Error parsing graphite line: api{h}.cpu {h}"
    runas = ("[2026/01/07-00:00:00.000] [t-1] [ERROR] [dip.scenarios.trigger.service]  - Failed to build trigger runner "
             "(PROJ.SC.abc), skipping: Cannot run scenario PROJ.SC: configured to run as user 'gone_user' which does not exist")
    log.write_text(log.read_text() + "\n".join(metric.format(h=h) for h in range(1, 4)) + "\n" + runas + "\n")
    out, facts = _facts_for(bundle)
    v = facts["backend_log"]["value"]
    top = {p["pattern"]: p for p in v["top_error_patterns"]}
    graphite = top["[dku.monitoring] Error parsing graphite line"]
    assert graphite["count"] == 3 and graphite["first"] == "2026/01/06-01:00:00" and graphite["last"] == "2026/01/06-03:00:00"
    assert v["run_as_user_missing"]["count"] == 1 and v["run_as_user_missing"]["scenarios"] == {"PROJ.SC": 1}
    assert v["run_as_user_missing"]["distinct_users"] == 1
    assert "gone_user" not in out


def test_crash_dumps_report_header_fields_only():
    dumps = run_facts("synthetic_design_baseline")["crash_dumps"]["value"]
    assert dumps["count"] == 1 and dumps["dumps"][0]["file"] == "hs_err_pid4242.log"
    assert dumps["dumps"][0]["cause"].startswith("There is insufficient memory")


def test_deployer_flags_a_remote_host_recorded_under_local_mode(tmp_path):
    bundle = mutated_bundle(tmp_path, "synthetic_design_k8s_remote", lambda doc: doc["deployerClientSettings"].update(mode="LOCAL"))
    _, facts = _facts_for(bundle)
    assert facts["deployer"]["value"]["remote_host_with_local_mode"] is True
    assert run_facts("synthetic_design_k8s_remote")["deployer"]["value"]["remote_host_with_local_mode"] is False


def test_groups_fact_reports_counts_only(tmp_path):
    bundle = mutated_bundle(tmp_path, "synthetic_design_baseline", lambda doc: None)
    mirror = next(bundle.rglob("general-settings.json")).parent
    (mirror / "users.json").write_text(json.dumps({"users": [], "groups": [
        {"name": "secret-admins", "sourceType": "LOCAL", "admin": True, "mayCreateProjects": True},
        {"name": "analysts", "sourceType": "LDAP", "admin": False, "mayManageUDM": False}]}))
    value, out = _facts_for(bundle)[1]["groups"]["value"], json.dumps(_facts_for(bundle)[1]["groups"])
    assert value == {"count": 2, "admin_groups": 1, "may_create_projects": 1, "may_manage_udm": 0,
                     "by_source_type": {"LOCAL": 1, "LDAP": 1}}
    assert "secret-admins" not in out
    assert run_facts("synthetic_design_k8s_remote")["groups"]["value"] == "ABSENT"


def test_local_deployer_fact_counts_files():
    v = run_facts("synthetic_design_baseline")["local_deployer"]["value"]
    assert v["project_deployer_infras"] == 1 and v["project_deployer_deployments"] == 1
    assert v["project_deployer_projects"] == "ABSENT" and v["api_deployer_services"] == "ABSENT"
    assert run_facts("synthetic_design_k8s_remote")["local_deployer"]["value"] == "ABSENT"
