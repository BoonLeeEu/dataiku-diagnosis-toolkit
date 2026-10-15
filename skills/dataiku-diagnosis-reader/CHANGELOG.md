# Changelog

All notable changes to the `dataiku-diagnosis-reader` skill package are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this package
adheres to [Semantic Versioning](https://semver.org/). The version tracked here is the one in
`SKILL.md`'s `version` frontmatter field — the two must always match.

Versioning is scoped to this directory (`dataiku-diagnosis-reader/`) only, since it's the unit
that gets copied/symlinked into a skills root independently of the rest of this repo.

## [0.22.0] - 2026-10-15

### Added

- New fact `groups`: group count, groups with admin rights, groups that may create projects or manage the user directory, and the count by source type, read from `config/users.json`. Names are never printed.
- New fact `local_deployer`: file counts under `config/project-deployer/{projects,infras,deployments}` and `config/api-deployer/{infras,published-services,deployments}`.
- `references/data-dir-config.md` documents both.

## [0.21.0] - 2026-10-14

### Added

- `scripts/facts.py` `backend_log` gains `top_error_patterns` (the ten most frequent ERROR/FATAL messages, normalised, with count, share and first/last timestamp) and `run_as_user_missing` (errors for scenarios configured to run as a user that no longer exists: scenarios, distinct-user count, window; user names never printed).
- New fact `crash_dumps`: per `run/hs_err_pid*.log` the process, cause, problem class and time, read from the header only.
- `deployer` gains `remote_host_with_local_mode`.
- `references/data-dir-runtime-and-codeenvs.md` and `references/data-dir-config.md` document the above.

## [0.20.1] - 2026-10-08

### Changed

- `SKILL.md` slimmed (164 to 113 lines) with no change to what it covers: orient is now workflow step 1 (was step 7); the list of every fact `facts.py` prints is replaced by its contract (`{fact: {value, source}}`, `ABSENT`, `ERROR`, no secrets), since the output is self-describing; node and mirror identification point to the references; the duplicated "Known limitations" section and the deployer-key secrets bullet are folded into their single homes; shorter reference index and description.

### Added

- `references/orient-fallback.md`: how to orient when `orient.sh` can't run where the bundle is (pipe it over stdin, or the manual commands), moved out of `SKILL.md`.

## [0.20.0] - 2026-10-08

### Added

- `scripts/facts.py` `connections` gains `cloud_storage` (per GCS, Azure or S3 connection: `readable_by_set`, `hdfs_interface_set`) and `warehouses` (per Snowflake, Databricks, Redshift, BigQuery or Synapse connection, SQL Server with `azureDWH` counting as Synapse: `fast_write`, `spark_native`, `udf`, each true, false or `ABSENT`). Types and booleans only, no params, hosts or credentials. The warehouse flags are found by setting-name pattern and a non-blank value counts as set, because only BigQuery (`useAutoFastPath`) and SQL Server could be checked in the three sample bundles; `references/data-dir-config.md` says so and corrects where `hdfsInterface` lives.

## [0.19.0] - 2026-10-07

### Added

- `scripts/facts.py` gains `kubernetes`: whether a Kubernetes cluster is attached (a `config/clusters/*.json` file or a default cluster id; the cluster files' `type` and `architecture` only), `implicit_cluster`, each container execution config (type, memory and CPU request/limit, namespace kind), each Spark execution config (executor and driver sizing, whether resources are set, `managed_kubernetes`, namespace kind, authentication mode), the container defaults (`default_execution_config` (the config's name), `default_visual_recipes_config_set`, `containerized_visual_recipes_enabled`) and `spark_enabled`. Namespaces read `templated`, `fixed` or `ABSENT`; no registry URLs or names are printed. Verified against the three sample bundles (the July design sample has a manual cluster, five container and three managed Spark configs; both GE August samples have three YARN-side Spark configs and no cluster). `references/data-dir-config.md` notes that the container defaults and `cdeEnabled` live inside `containerSettings`.

## [0.18.0] - 2026-10-07

### Added

- `scripts/facts.py` gains `metastore_and_exports`: the metastore catalog flavor, the estate signals that decide whether it fits (`hive_enabled`, `hadoop_enabled_in_host_env` from `diag.txt`), and `graphics_exports_enabled`; each `ABSENT` when not set. Verified against the three sample bundles (`HIVESERVER2` with Hive enabled on all three; graphics export off on the July sample).
- `scripts/facts.py` gains `backend_log`: per `backend.log*` file the lines at `ERROR`, `FATAL` and `WARN`, the lines naming an `OutOfMemoryError`, and the first and last timestamp, with totals. Streams each file (about 0.8 s for ~250MB per bundle), prints counts only, skips compressed rotations (`gz_files_skipped`). Counts a level only at the line's own level position; spot-checked against `grep` on a sample file (the few extra `grep` hits were `INFO` lines quoting a subprocess's `[ERROR]`). `references/data-dir-runtime-and-codeenvs.md` documents it.
- `scripts/facts.py` `admin_cleanup_scenarios`: each scenario gains `scripted` (true when it is not a step-based scenario, i.e. it runs a script that is never read), so a rule needn't know the scenario type names.

## [0.17.0] - 2026-10-07

### Added

- `scripts/facts.py` gains `genai_settings`: the default code envs for retrieval (RAG) and PII detection (`retrieval_code_env`, `pii_detection_code_env`; names, `ABSENT` when unset), the AI Services terms flag (`ai_services_terms_accepted`), the enable flags (`ai_services_enabled`: `enabled` on older DSS, per-feature flags on newer), and which Cobuild default LLM ids are set (`cobuild_default_llms_set`: set/unset per id, the ids are not printed; `ABSENT` when `agentBuildingSettings` is missing). Verified against the three sample bundles (internal envs on two, none set on the automation node; terms not accepted on all three; no Cobuild block on any). `references/data-dir-config.md` documents the keys.

## [0.16.0] - 2026-10-07

### Added

- `scripts/facts.py` gains `server_config`: whitelisted settings from `install.ini` `[server]` (`ssl`, whether a certificate is configured, and the ten security headers `content-security-policy`, `x-frame-options`, `x-content-type-options`, `x-xss-protection`, `hsts-max-age`, `referrer-policy`, `permissions-policy` and the three `cross-origin-*` ones, only those that are set) and from `config/dip.properties` (the five `dku.exports.disable*` keys that are set, `dku.wikis.authorizedUploadExtensions`, `dku.feature.dataTableLinks.enabled`). Certificate and key locations are reduced to yes/no. `dip_properties_present` is false when the file is not in the bundle (DSS only has it once the instance is customised, so an absent file means none of its keys are set). Verified against the three sample bundles (GE design: `ssl` true and `dku.exports.disableAllExports=true`; the July sample: six headers set and no `ssl`).

## [0.15.0] - 2026-10-07

### Added

- `scripts/facts.py` gains `security_settings`: the instance's security toggles from `config/general-settings.json` > `security`, as a whitelist (`hideErrorStacks`, `hideVersionStringsWhenNotLogged`, `sessionsMaxTotalTimeMinutes`, `sessionsMaxIdleTimeMinutes`, `forceSingleSessionPerUser`, `restrictUsersAndGroupsVisibility`, `postLogoutBehavior`, `sameSiteNoneCookies`, `secureCookies`, `enableEmailAndDisplayNameModification`, `disableDataTableLinks`), each `ABSENT` when not set. A custom post-logout URL is reduced to its scheme (`postLogoutCustomURL_scheme`) so no URL is printed. `ABSENT` as a whole when the file or its `security` block is missing. Verified against the three sample bundles (all carry every whitelisted key).

## [0.14.0] - 2026-10-07

### Added

- `scripts/facts.py` `sanity_check` gains `codes`: the distinct message codes in `run/sanity-check.json` (the code, or the title when a message has no code), sorted. These are fixed identifiers such as `WARN_PROJECT_LARGE_JOB_HISTORY`, so a check can tell whether DSS flagged a specific condition (for example a rotational data-directory disk) without the free-text `details`, which is never printed. Verified against the three sample bundles (2, 4 and 4 distinct codes).

## [0.13.0] - 2026-10-07

### Added

- `scripts/facts.py` `cgroups` gains `target_counts`: the number of cgroup targets configured for each workload category that has a `targets` list (e.g. `jobExecutionKernels: 0`). A category missing from the map is not in the settings at all, which `workload_categories_with_no_placement` cannot tell apart from a category with targets configured. Counts only; no target paths. Verified against the three sample bundles (`jobExecutionKernels` is present with 0 targets in all three).

## [0.12.0] - 2026-10-07

### Added

- `scripts/facts.py` gains `sanity_check`: whether `run/sanity-check.json` is in the bundle (`ABSENT` when it is not) plus `empty` (a blank file or no messages), its message count, counts by severity and fatal count. Handles both documented layouts (top-level `messages[]` and nested under `report`). Verified against the three sample bundles.

## [0.11.0] - 2026-10-06

### Added

- `scripts/facts.py` gains `byo_llm`: whether Bring Your Own LLM mode is active (a main LLM id or reference project key is set in `localAIServerSettings`; a CustomLLM connection alone does not count), the main/response-format/fast LLM ids and whether a reference project key is set. `ABSENT` when the block is missing. The field names come from Dataiku's checklist: the three sample bundles have the block but none populates them, so this is unverified against a populated sample (see `references/data-dir-config.md`).

## [0.10.0] - 2026-10-06

### Added

- `scripts/facts.py` gains three facts, verified against the design, automation and older design samples: `data_volume_device` (the data directory from `printenv` → the longest matching `lsblk` mount point → its backing disk(s) → ROTA from `lsblk -t`; `ABSENT` when the device can't be established), `admin_cleanup_scenarios` (housekeeping-project candidates with each scenario's `type`, `active`, trigger state and step names; scripts are never opened) and `deployer` (mode and target host; the API key is never printed, only whether one is configured). The `sso_and_ldap` fact also reports the LDAP authorized-groups count (names are not printed).
- Secrets guidance: `deployerClientSettings` holds a Deployer API key, so read it via `facts.py` or `peek.py --path`, never raw. A repeat-review run printed that key. Documented in `SKILL.md`; the key-masking is covered by the `peek.py` redaction.

## [0.9.0] - 2026-10-06

### Added

- `scripts/facts.py <bundle_root>`: one deterministic, secret-safe JSON report of the settings reviews most often need (node/version, heap sizes, host memory, `config/` size summed from `config_listing.txt`, internal database type/host/loopback, concurrency limits by leaf-key search, SSO/LDAP, impersonation rule counts, cgroup memory limit as % of host memory, `filesystem_root`, Trace Explorer, default connection/engine preferences, installed plugins/Agent Hub). Missing settings are an explicit `ABSENT`, never `false`/`0`. Added after repeat reviews of the same bundle disagreed because hand reads mis-stated or missed values. Verified against the design, automation and older design samples. Documented in `SKILL.md` step 8 and `lookup-table.md`.

## [0.8.0] - 2026-10-06

### Added

- Reference facts, spot-checked against the design and automation samples: how to find a housekeeping/admin project (no fixed name: `ADMINPROJECT`, `ADMINISTRATIONPROJECT`) and read its scenarios; `step_based` scenarios keep steps in `params.steps[]` (`runnable`), `custom_python` ones only `params.envSelection` plus a sibling `.py`. Added to `lookup-table.md` and `data-dir-config.md`.

## [0.7.0] - 2026-10-06

### Added

- Reference facts, spot-checked against the design and automation samples: the metastore flavor is `general-settings.json` → `metastoreCatalogsSettings.synchronizeTo.flavor` (`HIVESERVER2` in all three; other values unobserved), and `graphicsExportsEnabled` is a top-level boolean (`true`/`false` both seen). Added to `lookup-table.md` and `data-dir-config.md`.

## [0.6.0] - 2026-10-06

### Added

- Reference facts, spot-checked against the design and automation samples: user isolation (UIF) lives in `general-settings.json` → `impersonation` (`enabled`, `userRules[]`, `groupRules[]`, rule `type`/`scope`), separate from the `install.ini` `[mus]` OS wrapper. Added to `lookup-table.md` and `data-dir-config.md`.

## [0.5.0] - 2026-10-05

### Added

- `scripts/peek.py`: `--keys` (key names and types only) and `--max-items N` (the default 40 hid 64 of 104
  top-level keys in `general-settings.json`).
- Reference facts, spot-checked against the design and automation samples: `general-settings.json` →
  `security.sessionsMax*Minutes`, `forceSingleSessionPerUser`, `ipBoundSessions`, `disableDataTableLinks`
  (not UI-only); `users.json` → `groups[].canObtainAPITicketFromCookiesForGroupsRegex`; Agent Hub signals
  (`config/plugins/agent-hub`, `AGENT_HUB` project with a web app); `sanity-check.json` has no
  `lastRunTimestamp` (mtime only); `dmesg` timestamps are seconds since boot; logs can end after `diag.txt`'s date.

### Changed

- `peek.py` redacts only string values under a sensitive key name (booleans and numbers such as `hashApiKeys`
  are shown) and now also masks any `apiKey`.
- `SKILL.md` "Handling secrets": don't `head`/`cat` user scripts (a `grep -l` recipe counts hard-coded keys
  instead), never print a sub-object, a secret's length or prefix, or broad customer metadata.
- `SKILL.md` step 7: pipe `orient.sh` verbatim, not a condensed copy; note it needs bash (WSL/Git Bash on Windows).

## [0.4.1] - 2026-10-05

### Changed

- `SKILL.md` step 7: when `orient.sh` can't run where the bundle is, pipe it there (`bash -s -- <root>` with the
  script on stdin) before falling back to the by-hand commands. A plugin run on a linked computer had oriented
  by hand because the script lived in the plugin, not on the user's machine.

## [0.4.0] - 2026-10-04

### Added

- `scripts/peek.py`: secret-safe structural view of a bundle JSON file (keys, types, non-secret values;
  masks passwords, tokens, keys and embedded credentials; `--path` to drill to one key).

### Changed

- `SKILL.md` "Handling secrets": make `peek.py` the default way to open config JSON, and name the banned
  patterns (whole-file dumps of `general-settings.json`/`connections.json`/`users.json`, `printenv`,
  reading user scripts in full).
- `references/data-dir-config.md`: `connections.json` is `{"connections": {<name>: {...}}}` (spot-checked on
  design and automation bundles). A plugin run guessed a bare name-keyed dict and had to redo its script.

## [0.3.1] - 2026-10-04

### Changed

- `SKILL.md` step 7: say what to do when `scripts/orient.sh` can't run (bundle on a different machine from the
  skill folder): orient by hand with the equivalent read-only commands and say so.

## [0.3.0] - 2026-10-04

### Added

- `SKILL.md`: "Handling secrets" section (read only what is needed, extract specific keys, never copy
  secrets into outputs, report and rotate if printed).

### Changed

- `SKILL.md`: shorter `description`; "Quick lookup" trimmed to the highest-traffic rows (the full index
  stays in `references/lookup-table.md`); "Known limitations" reduced to a pointer plus the key caveats;
  step 7 now says to run `scripts/orient.sh` first when triaging a whole bundle; quoted frontmatter values.

## [0.2.0] - 2026-10-04

### Added

- `references/data-dir-config.md`: how to tell whether a Kubernetes cluster is attached
  (`config/clusters/` and `defaultK8sClusterId`), cluster `type`/`architecture`, observed
  deployer subtree shape, a "finding a setting reliably" section (leaf-key search, limits under
  other blocks, `dip.properties`/`install.ini`, feature-in-use signals) and connection
  `detailsReadability`/`params.root`/`hdfsInterface`.
- `references/data-dir-runtime-and-codeenvs.md`: backend log line format (bracketed levels),
  per-file time windows, `hs_err_pid*.log` header reading; `sanity-check.json` documented with both
  observed shapes and the codes seen.
- `references/root-files.md`, `data-dir-identity.md`, `listings-and-manifests.md`,
  `lookup-table.md`: `lsblk -t` `ROTA` column, `[javaopts]` heap keys, sizing `config/` from
  `config_listing.txt`, and matching lookup rows.

### Changed

- Facts from these additions that no sample could verify (`agentBuildingSettings`, an
  `INTERNAL_huggingface` code env, `jek.xmx`/`fek.xmx`, a populated `project-deployer/`'s
  `infras/` and `deployments/`, the `type` value of a DSS-provisioned cluster) are marked as
  unverified in the text rather than asserted.

## [0.1.0] - 2026-09-21

### Added

- Initial skill: `SKILL.md` 3-tier content model and step-by-step investigation workflow,
  `scripts/orient.sh`, and `references/` covering root files, the data-dir mirror (identity,
  config, runtime/code-envs), listings/manifests, node-type differences, the quick lookup table,
  and documented limitations.
- Spark-on-Kubernetes namespace fields documented in `references/data-dir-runtime-and-codeenvs.md`.

[0.2.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/releases/tag/skill-v0.2.0
[0.1.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/releases/tag/skill-v0.1.0
