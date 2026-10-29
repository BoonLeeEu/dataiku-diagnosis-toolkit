# `<mirror>/` runtime logs, code environments, plugins, and support config

All paths below are relative to the data-dir mirror root (see `references/data-dir-identity.md`).

## Code environments

**`code-envs/desc/python/<env-name>/`** — centrally/admin-managed Python environments (common on
design nodes; may be empty on an automation node):

- `desc.json` — env definition: `pythonInterpreter`, `corePackagesSet`, `deploymentMode`, creation/
  modification tags (who/when)
- `spec/requirements.txt`, `spec/environment.spec` — the **requested** spec (can be blank/unset)
- `actual/requirements.txt` — the **actually resolved, pinned** package list (e.g.
  `absl-py==2.3.1`) — **this is the answer to "what packages/versions are installed in env X"**,
  not `spec/requirements.txt`
- `actual/info.json` — build metadata (often minimal)
- `code-envs/logs/python/<env>/*.log` — install/build logs (pip resolution errors, etc.): `createPythonEnv.log`, `updateEnvAccordingToSpec.log`, `installJupyterSupport.log`, `removeJupyterSupport.log`, `fetchDetails.log`. Pip transcripts with no timestamps or level token
- Often has an internal `.git` history tracking env spec changes over time

**`acode-envs/python/<name>/`** — "activated code-envs", auto-created when a bundle activates on a
node. The collector scans this path on every node type (`find code-envs/desc acode-envs/desc -ls`
runs regardless of `nodetype`), but it's typically empty on design nodes and populated on
automation nodes where bundles get activated. Same shape as `code-envs/` (`desc/{spec,actual}/...`),
with build/activation logs at `acode-envs/logs/python/<env>/*.log` (`importPythonEnv.log`,
`handleCodeEnv.log`, `createEnv.log`, `updateEnvFolderAccordingToSpec.log`,
`installJupyterSupport.log`). **Capture-completeness caveat**: in the sample surveyed, only the
logs were physically mirrored into the bundle — the `desc/{spec,actual}` files themselves were
visible only via `datadir_listing.txt`, not as real files. Verify per-bundle.

## `caches/`

Backend runtime JSON caches — generally low troubleshooting value, with two automation-flavored
exceptions:

- `reflected-events-v.json` — on automation nodes, doubles as a **bundle-activation audit trail**:
  repeated `{"message": "bundle-activate", ...}` entries with timestamps.
- `reflected-events-p.json` — observed capturing failures of `unified-monitoring/automation/
  project-scenarios-run` and `.../project-models-status` public API calls (automation/MLOps
  monitoring endpoints).
- `reports.json` — cached `project-usage-summary-<PROJECT>` reports.

## `install-support/`

- `nginx.conf`, `supervisord.conf` — generated reverse-proxy and process-supervisor configs
- `backends.d/<NAME>/<id>.conf` — per-project/webapp nginx routing (folder names reveal registered
  webapps/special backends, e.g. deployed API endpoints). Notably absent on the automation sample
  surveyed.

## `plugins/dev/<plugin>/`

Locally-developed plugin **source code**: `plugin.json`, `python-lib/`, `python-runnables/`,
`custom-recipes/`, `webapps/`, `code-env/`, `parameter-sets/`, often with `README.md`/
`Jenkinsfile`/`CHANGELOG.md`. Populated on design nodes where plugin development happens; present
as an **empty placeholder directory** on automation nodes (the schema reserves the slot, but no
dev activity occurs there). This is separate from `config/plugins/<id>/settings.json`, which
records install/enable state on *any* node type (see `references/data-dir-config.md`).

## `run/` — live runtime logs and state

| File | Contains | Notes |
|---|---|---|
| `backend.log` (+ `.1`/`.2` rotated) | Main DSS backend Java process log: API call traces (`[dku.tracing] Start call: ... user=...`), job/scenario status, exceptions | **Primary app log** for "what happened and when" |
| `frontend.log.0`-`.4` | Browser-side UI log (one DEBUG pair per API call) | `.0` is newest, `.4` oldest; no unnumbered file |
| `nginx.log` (+ rotated) | Reverse-proxy **error** log (no access lines); may open with `nginx: [alert] could not open error log file` | Mostly 404 noise; see `references/logs.md` |
| `ipython.log` (+ rotated) | Jupyter/ipython gateway process log | |
| `eventserver.log` (+ rotated) | Usage-tracking/telemetry log | |
| `supervisord.log` | Process-manager log: start/stop/restart events for backend/frontend/nginx/ipython/eventserver | Crashes (`exited ... not expected`, `gave up ... entered FATAL state`) are logged at INFO/WARN, not ERROR |
| `install.log` | Full install/upgrade transcript | Can be ~90-100MB+; never load whole |
| `install-impersonation.log` | `dssadmin install-impersonation` output — sets up the OS-user impersonation wrapper referenced by `install.ini`'s `[mus] exec_wrapper_location` | Most operationally relevant for scheduled/unattended job execution (automation) |
| `hs_err_pid<N>.log` | **JVM fatal crash dumps** (HotSpot error logs) — native-mmap OOM failures, thread/heap/register dump | Primary source for crash/OOM root-cause; cross-reference with `dmesg.txt` (OOM-killer) and `cgroups_usage.txt` (which project/activity was responsible). Not observed in the one automation sample surveyed — absence doesn't rule it out generally |
| `sanity-check.json` | DSS's own self-diagnostic warnings: `messages[]` of `{severity, isFatal, code, title, details, message}`. The array is at the top level in two samples and nested under `report.messages` (beside `lastRunTimestamp`) in a third — handle both. No `lastRunTimestamp` in the two top-level-`messages` samples, so the last-run time is only the file's mtime (which can be months before the bundle date) | Surfaces real misconfigurations DSS itself flagged. Codes seen: `WARN_CONNECTION_SPARK_NO_GROUP_WITH_DETAILS_READ_ACCESS`, `WARN_MISC_EVENT_SERVER_NO_TARGET`, `WARN_MISC_DISK_ROTATIONAL` (data dir on a rotational disk), `WARN_SECURITY_PROCESS_TYPE_WITHOUT_MEMORY_LIMIT` (no cgroup memory limit for a process type), `WARN_MISC_BASE_IMAGE_NOT_FOUND` (missing container base image). These are DSS's own findings, so they are first-hand evidence for the matching host/resource/connection questions |
| `user-last-activity.json` | Per-login last activity/login timestamps | Can reveal auth/attack attempts in login strings. Not observed in the automation sample surveyed |
| `cde-images.json`, `built-base-images.json` | Code-env-in-container / Code Studio image build records | Not observed in the automation sample surveyed (consistent with no Code Studio building there) |
| `audit/audit.log.N` | Rotated audit trail (user actions) | Often ~100MB each. **Not observed as real content in any of the 3 samples surveyed** — only as path/size entries in `datadir_listing.txt`. Don't assume it's ever mirrored as content; verify per-bundle before promising to read it |

## Reading the logs

For errors and warnings across all the logs, use `scripts/logscan.py` and `references/logs.md` (per-log formats, signatures, masking).

**Line format.** `backend.log` lines look like `[2026/07/21-08:56:51.095] [thread] [LEVEL] [logger]
- message`: the level is a **bracketed token mid-line**, after the timestamp and thread name. Match
`\[ERROR\]` / `\[FATAL\]` / `\[WARN\]`; a line-anchored pattern such as `^ERROR` returns a false
zero.

**Counts.** `facts.py` `backend_log` streams every `backend.log*` file once and reports, per file, the lines at `ERROR`, `FATAL` and `WARN`, the lines naming an `OutOfMemoryError`, and the file's first and last timestamp (counts only, no log text; compressed rotations are skipped and counted). It counts a level only in the line's own `[LEVEL]` position, so subprocess output that quotes another log line (an `INFO` line carrying a nested `[ERROR]`) is not counted as an error; a looser `grep` for `[ERROR]` reads a few percent higher.

`backend_log` also reports `top_error_patterns`: the ten most frequent `ERROR`/`FATAL` messages, grouped by logger and first clause and masked exactly as `logscan.py` does (see `references/logs.md`), each with a count, its share of all errors and its first/last timestamp. Quote a dominant pattern's share from here instead of a hand `grep`. `run_as_user_missing` counts the errors `Cannot run scenario <project.scenario>: configured to run as user '<name>' which does not exist` (a scenario whose owner was deleted: its trigger is skipped each time the trigger list rebuilds, so one scenario can produce thousands of lines), with the affected scenarios, a count of distinct users (never the names) and the window.

**Time window.** Each rotated file covers a very different span: in the samples a file covered
anywhere from ~1 hour (a busy design node) to ~3 days, so the same count means different things
for different files. Take the first and last timestamp of **each** file so any count can be quoted
with the window it covers: `head -1` for the first, and for the last the final line that starts
with `[` (a file can end mid stack-trace, e.g. `at java.base/...`). Rotation order: `backend.log`
is newest, then `.1`, `.2` progressively older.
The logs can end later than `diag.txt`'s own `date` line (seen: ~19 minutes), so the bundle has no single
generation instant; quote each file's own window.

**JVM crash dumps.** `hs_err_pid*.log` is large. Read only the header, the lines starting with
`# ` (`grep '^# '`, first ~20): they state the cause (e.g. "There is insufficient memory for the
Java Runtime Environment", "Native memory allocation (mmap) failed to map N bytes") and
distinguish an OOM from a segfault (`SIGSEGV`). Never read the whole file. `facts.py` `crash_dumps` does this: per dump the process (the main class named by `java_command`, e.g. `DSSBackendMain` or `DSSJobKernelMain`), the cause line, the problem class (`Out of Memory Error`, `Internal Error`, `SIG...`) and the dump's `Time:`. The dump's own time is the date to quote, not the file's mtime.

Cross-reference: when investigating a crash, check `hs_err_pid*.log` timestamps against
`dmesg.txt` OOM-killer entries and `cgroups_usage.txt` to identify which project/activity type was
responsible for the memory pressure.
