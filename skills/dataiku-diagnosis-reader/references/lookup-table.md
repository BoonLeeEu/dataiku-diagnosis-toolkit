# Full "where do I find X" lookup table

`<mirror>` = the data-dir mirror root (see `references/data-dir-identity.md`). All paths are
relative to it unless a root-level bundle file is named directly.

## Identity, health, versions

| Question | Where | Notes |
|---|---|---|
| Is the data directory on a rotational disk (SSD check) | `scripts/facts.py` → `data_volume_device`; source blocks in `diag.txt`: `printenv` (`DIP_HOME`), `lsblk`, `lsblk -t` | Data dir → longest matching mount point in the `lsblk` tree → backing disk → `ROTA` (0 = SSD, 1 = rotational). An LVM volume's disk is the root of its tree. `ABSENT` when no matching mount or no listing. DSS's own `run/sanity-check.json` may also flag it but can be missing |
| Several key settings at once (heap sizes, host memory, `config/` size, DB host, concurrency limits, SSO, UIF, cgroups, `filesystem_root`, Agent Hub, GenAI defaults, metastore flavor, graphics export, backend-log error counts, Kubernetes and Spark execution configs) | `scripts/facts.py <bundle_root>` | JSON `{fact: {value, source}}`; `ABSENT` = not in the bundle (not `false`/`0`); never prints secrets. Config size is summed from `config_listing.txt`, not `du` of the partial mirror |
| DSS version | `dss-version.json` | `product_version`, `conf_version` |
| Node type (design/automation/...) | `install.ini` → `[general] nodetype` | See `references/node-types.md` |
| Is DSS running? Which components, PIDs, uptime? | `diag.txt` → `dss status` section | |
| OS/runtime versions, CPU/memory/disk, network, env vars, ... | See the dedicated **OS / system / environment** section below | Most of this is inlined in `diag.txt` — check there first |
| OS packages | `syspackages.txt` (`rpm -qa`) | |
| DSS-bundled Python packages (not project code-envs) | `pip.txt` | |
| R packages | `r.txt` | May be absent even if the command ran — see `references/limitations.md` |
| DSS self-diagnostic warnings | `run/sanity-check.json` | |

## OS / system / environment (check `diag.txt` first — a lot of this is inlined there)

| Question | Where | Notes |
|---|---|---|
| Kernel version, architecture, hostname | `diag.txt` → `uname -a` | |
| OS user DSS runs as | `diag.txt` → `id` | Cross-check with `printenv`'s `USER`/`HOME` |
| Host uptime / load average | `diag.txt` → `uptime` | |
| OS distro & version | `diag.txt` → `/etc/redhat-release`/`lsb_release -a`, or `printenv`'s `DKUDISTRIB` | |
| SELinux mode | `diag.txt` → `getenforce` | |
| Node type — fast path | `diag.txt` → `printenv`'s `DKU_NODE_TYPE` | Faster than parsing `install.ini` |
| JVM heap size per DSS component | `diag.txt` → `printenv` (`DKU_BACKEND_JAVA_OPTS`, `DKU_EVENTSERVER_JAVA_OPTS`, etc.) | Check before/alongside `install.ini`'s `backend.xmx` |
| Ports per DSS component | `diag.txt` → `printenv` (`DKU_NGINX_PORT`, `DKU_BASE_PORT`, `DKU_BACKEND_PORT`, ...) | |
| Is Spark/Hadoop integration enabled | `diag.txt` → `printenv` (`DKU_SPARK_ENABLED`, `DKU_SPARK_VERSION`, `DKU_SPARK_HOME`) | |
| Installed Java/Python/nginx/conda versions | `diag.txt` → the version-probe sections | Two JVMs can coexist (DSS-bundled vs. system) |
| CPU model / core count | `diag.txt` → `/proc/cpuinfo` | Count entries for logical core count |
| Memory total/used/free/swap | `diag.txt` → `free -m`, `/proc/meminfo` | `/proc/meminfo` has finer detail (hugepages, commit limit) |
| Memory-overcommit / swappiness tuning | `diag.txt` → `vm.overcommit_memory`/`vm.overcommit_ratio`/`vm.swappiness` | Relevant to OOM behavior |
| Resource limits (open files, max processes, core size) | `diag.txt` → `ulimit -a` (soft) / `ulimit -a -H` (hard) | A soft core-size limit of 0 explains missing core dumps even with a permissive hard limit |
| Disk space / inode usage per filesystem | `diag.txt` → `df -h` / `df -i` | Check here before assuming you need `datadir_listing.txt` for disk pressure |
| Block device / partition / LVM layout | `diag.txt` → `lsblk` / `lsblk -t` | |
| SSD vs. rotational disk for the data dir | `diag.txt` → `lsblk -t` `ROTA` column (`0` = SSD, `1` = rotational), plus `run/sanity-check.json` → `WARN_MISC_DISK_ROTATIONAL` | Match the row to the volume holding the data dir — see `references/root-files.md` |
| Filesystem UUIDs, active mount options, fstab | `diag.txt` → `blkid`/`mount`/`/etc/fstab`/`/etc/mtab`/`findmnt` | **Version-dependent** — seen on newer DSS (14.4.3), absent on older (14.2.1); check presence rather than assuming |
| cgroup hierarchy version (v1 vs v2) — as actually mounted on the host | `diag.txt` → `/proc/mounts` | Separate `/sys/fs/cgroup/<controller>` mounts = v1; one unified mount = v2. Cross-check against DSS's own `cgroupSettings.cgroupsVersion` in the **Resource governance** section below — they should agree |
| Network interfaces / IPs | `diag.txt` → `ip addr ls` | |
| Routing table | `diag.txt` → `ip ro ls` | |
| Full DSS environment variables (all of the above + more) | `diag.txt` → `printenv` | See `references/root-files.md`'s dedicated `printenv` breakdown — the richest single section in the bundle |
| Live CPU/memory/swap/IO over a sampling window | `diag.txt` → `vmstat 3 6` (and `iostat -x -c 3 6` if present) | 6 samples over ~18s, not just a point-in-time snapshot |
| Kernel-level ring-buffer log, incl. OOM-killer events | `dmesg.txt` | `grep -i 'oom-kill\|killed process' dmesg.txt` — names the responsible cgroup path (project + activity type) and RSS at kill time directly. Separate root file, not inlined in `diag.txt` |
| Full kernel parameter dump | `sysctl.txt` | Key tunables worth a targeted grep: `fs.file-max`, `fs.aio-max-nr`, `vm.max_map_count`, `kernel.pid_max`/`threads-max`, `net.core.somaxconn`, `net.ipv4.ip_local_port_range`, `crypto.fips_enabled`. Separate root file, not inlined in `diag.txt` |
| Full process tree, JVM command lines, top memory consumers | `ps.txt` | Grep `java` for exact per-component JVM flags; sort by RSS (column 6) to rank processes by memory independent of cgroups. Separate root file, not inlined in `diag.txt` |
| Confirm which TCP/unix ports are actually listening, and by what | `sockets.txt` | `grep -E '^tcp\s+LISTEN'` / `^u_str LISTEN'` — more detail than `diag.txt`'s `ip addr`/`ip route` |
| JVM thread dump / deadlock triage | `stacks.txt` | Count thread states first (`grep -oE ' (RUNNABLE\|WAITING\|TIMED_WAITING\|BLOCKED)' stacks.txt \| sort \| uniq -c`); a nonzero `BLOCKED` count on a shared lock is the real deadlock signal |
| Code-env container/K8s images (name, registry, size, build time) | `docker_images_listing.txt` | Only present when container exec is configured |
| OS package versions (security/compat questions) | `syspackages.txt` | Targeted grep beats reading ~1000 lines: `grep -iE '^(openssl\|glibc\|python3\|java-\|nginx\|systemd\|kernel)-[0-9]'` |

## Crashes, performance, resources

| Question | Where | Notes |
|---|---|---|
| Backend crash / OOM | `dmesg.txt` + `run/hs_err_pid*.log` + `cgroups_usage.txt` | Cross-reference timestamps and cgroup path to find the responsible project/activity |
| Thread hang / deadlock | `stacks.txt` | JVM thread dump — see the OS/system section above for the triage grep |
| Which diagnosis step was slow/huge | `timings.txt` | |
| Per-project/per-activity resource usage, ranked | `cgroups_usage.txt` | Paths like `/DSS/<project>/<activityType>`; sort by the memory column to find the top consumer |
| Manually patched env scripts (possible tuning cause) | `bin_listing.txt` (look for `_original`/`_modified`/dated-backup files) | |

CPU/memory/disk snapshots, kernel tunables, and network basics are covered in the **OS / system /
environment** section below — check there first before assuming you need `sysctl.txt`/`ps.txt`.

## Resource governance: cgroups, containers, Spark, Kubernetes

These settings are **spread across several blocks that must be read together** — a question like
"how are resources requested from the k8s cluster" is rarely answered by one field alone. See
`references/data-dir-config.md`'s dedicated subsection for the full field breakdown before
answering.

| Question | Where | Notes |
|---|---|---|
| How DSS confines process resource usage on this host (config, not live usage) | `config/general-settings.json` → `cgroupSettings` | Per-workload-type `cgroupPathTemplate`s. Cross-check against the *live* view in root file `cgroups_usage.txt` |
| K8s/Docker execution profiles for non-Spark containerized recipes/webapps | `config/general-settings.json` → `containerSettings.executionConfigs[]` | Each profile's `kubernetesResources` (`memRequestMB`/`memLimitMB`/`cpuRequest`/`cpuLimit`) is the actual ask sent to k8s |
| Spark execution profiles / how Spark requests resources, incl. on k8s | `config/general-settings.json` → `sparkSettings.executionConfigs[]` | `spark.executor.*`/`spark.driver.*` conf = the resource ask; `spark.kubernetes.*` conf = how it's packaged for the k8s scheduler |
| Is a Kubernetes cluster attached at all? | `config/clusters/` (any `<name>.json`) **and** `config/general-settings.json` → `defaultK8sClusterId` | None of either = no cluster attached. A cluster file's `type` (e.g. `manual`) says how it was registered — see `references/data-dir-config.md` |
| Implicit vs. explicit k8s execution setup | `config/general-settings.json` → `useImplicitK8sCluster` | `true` + empty `executionConfigs` = implicit; `false` + populated `executionConfigs`/a manual `clusters/*.json` = explicit |
| Per-cluster overrides of instance-wide Hadoop/Hive/Impala/Spark/container defaults | `config/clusters/<name>.json` → `override*Settings` blocks | Only overrides where the matching boolean sub-field is `true`; otherwise falls through to `general-settings.json` |
| Which named profile a specific recipe/job actually uses | `config/projects/<KEY>/recipes/<name>.json` → `params.engineParams.spark.sparkConfig.inheritConf` / `params.engineParams.containerSelection` | Confirmed for a Spark-engine recipe in one sample; verify the field name before asserting for other recipe/scenario/notebook types |
| Container/K8s images actually built for these profiles | `docker_images_listing.txt` (root file) | Only present when container execution is configured |
| Kerberos/YARN-based Hadoop defaults (as opposed to container-based Spark) | `config/general-settings.json` → `hadoopSettings` | `kerberosLoginEnabled`, `dssPrincipal`, `dssKeytabPath` |
| Which metastore catalog DSS syncs managed datasets to | `config/general-settings.json` → `metastoreCatalogsSettings.synchronizeTo.flavor` | Nested one level down, not `metastoreCatalogsSettings.flavor`. `HIVESERVER2` in all three samples (each also has `hiveSettings.enabled` true and a `hadoopSettings` block, a Hadoop estate), with `glueCredentialsMode` beside it. Other flavor values (Glue, DSS-internal) are not observed in any sample; don't guess their spelling. Whether datasets actually sync is not in the bundle |
| Is PDF/image (graphics) export of the Flow enabled | `config/general-settings.json` → `graphicsExportsEnabled` | Plain boolean: `true` in the 2026-08 design and automation samples, `false` in the 2026-07 design sample. Separate from `dip.properties`' `dku.exports.*` and from `security.requireProjectAdminPermissionToExportAndBundleProjects`. If the key is absent, treat it as unknown, not off |
| Is DSS's internal database H2 (default) or an external PostgreSQL | `config/general-settings.json` → `internalDatabase.connection` | Present + `connection.type` (e.g. `"PostgreSQL"`) = external server (params incl. plaintext password — sensitive); **absent** = default embedded H2 (inferred, no literal `"H2"` string observed). Don't confuse with the always-present `databases/*.mv.db` files — see `references/data-dir-config.md` |

## Users, security, connections

| Question | Where | Notes |
|---|---|---|
| Users/groups/permissions | `config/users.json` | Contains hashed passwords, PII |
| Data connections | `config/connections.json` → `connections.<name>` | Who may read a connection's details: `detailsReadability` (`readableBy`, `allowedGroups`); see `references/data-dir-config.md`. Never dump whole connections (use `scripts/peek.py`) — `params` can hold secrets |
| LDAP/SSO/proxy/mail/job-concurrency settings | `config/general-settings.json` | Job-concurrency limits can sit under another block (e.g. `jekSettings.maxRunningJobs`) — search the whole file for the leaf key, see `references/data-dir-config.md` |
| Advanced security/behaviour keys (header settings, `dku.feature.*`, upload extensions) | `config/dip.properties` **or** `install.ini` **or** `config/general-settings.json` | Search all three before calling a setting absent |
| Session timeouts, single-session, disabled table links | `config/general-settings.json` → `security.sessionsMaxTotalTimeMinutes`, `sessionsMaxIdleTimeMinutes`, `forceSingleSessionPerUser`, `disableDataTableLinks` | `0` minutes means no limit; not UI-only, see `references/data-dir-config.md` |
| Is user isolation (UIF / OS-user impersonation) on, and for whom | `config/general-settings.json` → `impersonation` | `enabled`, plus `userRules[]` / `groupRules[]` (each has a `type`, `IDENTITY` or `SINGLE_MAPPING`, and a `scope`). Count rules rather than printing `targetUnix`/`targetHadoop` (account names). The OS wrapper/install log row above only shows the wrapper was installed, not that the setting is on; whether the mapped OS users exist is not in the bundle |
| Is there a housekeeping (admin/maintenance) project with active cleanup scenarios | `config/projects/<KEY>/scenarios/<name>.json` | There is no fixed project name: `ADMINPROJECT` in two samples, `ADMINISTRATIONPROJECT` in the third, so list the keys under `config/projects/` and match on name (admin, maint, housekeep, cleanup). Read `type`, `active` and `triggers[].type`/`.active`. A `step_based` scenario keeps its steps in `params.steps[]` (`type: runnable`, names like "Clear Job logs"). A `custom_python` scenario has only `params.envSelection`; its logic is in a sibling `<name>.py`, which you should not open (scripts can hold keys). Run history is not in the bundle |
| Which groups may get webapp API tickets | `config/users.json` → `groups[].canObtainAPITicketFromCookiesForGroupsRegex` | Regex; empty = none |
| Is an optional feature (GenAI, local Hugging Face, Agent Hub) in use | `config/general-settings.json` → `localAIServerSettings.*UseLocal`, `generativeAISettings` | See `references/data-dir-config.md` for what is and isn't verified |
| JVM heap per component | `install.ini` → `[javaopts]` (`backend.xmx`; other `*.xmx` keys only when set) and `diag.txt` → `printenv` `DKU_*_JAVA_OPTS` | Size of `config/` for heap-vs-config checks: sum `config_listing.txt` — see `references/listings-and-manifests.md` |
| License/entitlements | `config/license.json` | May be an opaque signed blob |
| API keys | `config/personal-apikeys.json`, `config/public-apikeys.json` | |
| Login/auth activity | `run/user-last-activity.json` | Not observed in every bundle |
| Is this node a deployment target or a deployer host? | `config/general-settings.json` → `deployerClientSettings.mode` | `"REMOTE"` = target; presence of `config/api-deployer/`/`config/project-deployer/` = deployer host |
| Govern MLOps integration | `config/general-settings.json` → `governIntegrationSettings` | |

## Projects, code, plugins

| Question | Where | Notes |
|---|---|---|
| A specific project's recipes/datasets/scenarios/notebooks/dashboards | `config/projects/<KEY>/...` | See `references/data-dir-config.md` for the full subtree |
| Installed + enabled plugins | `config/plugins/<id>/settings.json` (folder names = plugin IDs) | On any node type |
| Plugin **source code** (dev) | `plugins/dev/<id>/` | Populated on design nodes with dev activity; empty placeholder on automation |
| Code-env resolved package versions | `code-envs/desc/python/<env>/actual/requirements.txt` | Not `spec/requirements.txt` (that's the request, not the resolution) |
| Automation-activated code-env package versions | `acode-envs/python/<name>/desc/actual/requirements.txt` (if physically mirrored) or `acode-envs/logs/python/<env>/*.log` | See capture-completeness caveat in `references/node-types.md` |
| Which bundle is activated for a project | `config/projects/<KEY>/active-bundle.json` | Mainly automation; can rarely appear on design (e.g. bundle test-activation) |
| Bundle activation history | `caches/reflected-events-v.json` (`"message": "bundle-activate"` entries) | Automation-flavored |

## Logs and traces

| Question | Where | Notes |
|---|---|---|
| Backend/API/job/scenario execution trace | `run/backend.log*` | Primary application log. Levels are bracketed (`[ERROR]`); record each file's first/last timestamp so counts carry a time window — see `references/data-dir-runtime-and-codeenvs.md` |
| Cause of a JVM crash | `run/hs_err_pid*.log` header (`grep '^# '`, first ~20 lines) | OOM vs. segfault is stated there; never read the whole file |
| Errors and warnings across all the major logs, grouped by pattern | `scripts/logscan.py <bundle_root>` | Streams every log, masks excerpts; `--around TS --timeline` narrows to an incident; formats and signatures in `references/logs.md` |
| Frontend errors | `run/frontend.log.*` | Browser-side UI log; mostly DEBUG |
| Reverse-proxy errors | `run/nginx.log*` | Error log only, no access lines |
| Jupyter/ipython gateway issues | `run/ipython.log*` | |
| Process start/stop/restart history | `run/supervisord.log` | |
| Install/upgrade history | `run/install.log` | Can be huge (~90-100MB+) |
| Scheduled-job OS-user impersonation setup | `run/install-impersonation.log`, `install.ini`'s `[mus] exec_wrapper_location` | |
| User action audit trail | `run/audit/audit.log.N` | Not observed as real content in any sample surveyed — typically listing-only in `datadir_listing.txt` |

## Full inventories (metadata only — no content)

| Question | Where |
|---|---|
| Every file in the whole data dir (name/size/date only) | `datadir_listing.txt` |
| Every file in the install dir (name/size/date only) | `installdir_listing.txt` |
| Every file under `config/` | `config_listing.txt` |
| Every file under `lib/` (JDBC drivers, java libs) | `lib_listing.txt` |
| Every file under `code-envs/desc/` | `code_envs_desc_listing.txt` |

## The content gap — check this before promising an answer

**Job run history, scenario run logs, dataset build timelines, and (often) audit-log content are
NOT included as retrievable content.** They typically show up only as path/size/date entries in
`datadir_listing.txt`. If asked for this kind of history, check `datadir_listing.txt` for
existence/size/last-modified and say plainly that the content itself isn't in the bundle — see
`references/limitations.md`.
