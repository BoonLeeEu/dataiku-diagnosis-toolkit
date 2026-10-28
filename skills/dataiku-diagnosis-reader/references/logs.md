# Reading the logs for errors and warnings

Every log below is large (rotated files run to ~100MB, ~1GB per bundle). Never load one whole. Run
`scripts/logscan.py <bundle_root>` once: it streams each file and returns, per log, the files with size and
time window, WARN/ERROR/FATAL totals, and one finding per normalised message pattern (count, first/last
timestamp, `file:line` of the first sighting, masked excerpt). `--log ID` limits it, `--top N` sets the findings
kept per log (default 30), `--no-excerpts` drops all log text. About 20 seconds for a design node.

Log ids: `backend`, `frontend`, `nginx`, `ipython`, `eventserver`, `supervisord`, `install`,
`install-impersonation`, `codeenv`, `dmesg`, `stacks`, `hs_err`. A log the bundle lacks comes back
`"present": false` with where it looked; absence is not evidence the log was clean.

`backend` and `hs_err` are also covered by `facts.py` (`backend_log`, `crash_dumps`); `logscan.py` groups the same
errors but keeps excerpts and does the other logs too.

## Line formats

Level is the token to match; each log writes it differently. A pattern anchored at the line start (`^ERROR`) returns
a false zero for the bracketed logs.

| Log | Files (in `run/` unless noted) | Line shape | Levels |
|---|---|---|---|
| backend | `backend.log`, `.1`, `.2` | `[2026/08/13-14:02:07.581] [thread] [LEVEL] [logger]  - message`, stack traces on the lines after | DEBUG INFO WARN ERROR FATAL |
| frontend | `frontend.log.0`–`.4` | `[2026/08/13-14:34:35] [session-id] [LEVEL] [logger]  - message` (no milliseconds). Browser-side UI log: one DEBUG pair per API call, so ~95% of lines are DEBUG | DEBUG INFO WARN ERROR |
| ipython | `ipython.log`, `.1`, `.2` | `[ts.ms] [pid/Thread] [LEVEL] [logger] [dku_call_id=x]  message`, mostly INFO call traces carrying `user=` | INFO WARNING ERROR (the level is `WARNING`, not `WARN`) |
| eventserver | `eventserver.log`, `.1`, `.2` | Same bracketed shape as backend with a thread name; the first line is an unbracketed `Loading plugins:` | INFO DEBUG WARN ERROR |
| supervisord | `supervisord.log` | `2026-08-13 05:30:00,654 LEVEL message`, no brackets (Python logging) | INFO WARN ERROR CRIT, see below |
| nginx | `nginx.log`, `.1`, `.2` | **Error log only, no access lines.** `2026/07/28 08:26:10 [error] 11642#11642: *8971019 message, client: ..., server: , request: "..."`. May open with `nginx: [alert] could not open error log file ... (13: Permission denied)` repeated per start | warn error crit alert emerg |
| install | `install.log` | Several installer runs appended (banner `Data Science Studio installer: <date>` and the command line, which includes the licence file name). Mixed: bracketed `[INFO]`/`[DEBUG]`/`[WARN]`, bare `WARNING:`/`ERROR:root:` lines from helper scripts, Java exception lines, `+ ` shell trace lines | as seen |
| install-impersonation | `install-impersonation.log` | Banner plus `[INFO]`, `[DEBUG]`, `[+]` lines | |
| codeenv | `code-envs/logs/python/<env>/*.log`, `acode-envs/logs/python/<env>/*.log` | A pip/virtualenv transcript, **no timestamps, no level token**: `ERROR: ...`, `error: ...`, `WARNING: ...` | |
| dmesg | `dmesg.txt` (bundle root) | `[  12345.678] message`, seconds since boot, not wall-clock | |
| stacks | `stacks.txt` (bundle root) | jstack: `"thread-name" #N ...` header, then `java.lang.Thread.State: BLOCKED (...)` | |
| hs_err | `hs_err_pid<N>.log` | HotSpot crash dump; read the `# ` header only | |

Rotation: a higher number is older, the unnumbered file is the newest. `frontend.log` has no unnumbered file: `.0`
is the newest and `.4` the oldest. Rotated files are ~100MB each (frontend ~50MB). Each file's window is its own, so
quote the first and last timestamp with every count (a file can end mid stack trace, so the last timestamp is the last
line that starts a record). `install.log` and `supervisord.log` are not rotated and span years; `codeenv` and
`dmesg` logs have no wall-clock window.

## Signatures that the level token does not give you

- **supervisord logs its worst events below ERROR.** `gave up: <proc> entered FATAL state, too many start retries too
  quickly` is logged at INFO. `exited: <proc> (exit status N; not expected)` and `exited: <proc> (terminated by SIGABRT
  (core dumped); not expected)` are process crashes. `killing '<proc>' (<pid>) with SIGKILL` (WARN) means a process
  ignored a stop request. `logscan.py` rates the first three ERROR whatever their level.
- **backend.log:** a line naming `OutOfMemoryError` counts as an error whatever its level. `Cannot run scenario ...:
  configured to run as user '...' which does not exist` is a scenario whose owner was deleted.
- **nginx.log:** one `[error]` pattern dominates on any busy node: `open() "<path>" failed (2: No such file or
  directory)` and `"<path>" is not found`, i.e. 404s for static files and scanner probes (paths such as
  `/.well-known/...`, `cgi-bin`, OGNL/`${...}` payloads). Those are noise or attack attempts, not DSS faults. The ones
  that matter: `connect() failed (111: Connection refused) while connecting to upstream` (the backend was down),
  `upstream timed out`, `upstream prematurely closed connection`, and `[emerg] cannot load certificate key`.
- **ipython.log:** `Uncaught exception in ZMQStream callback` and `zmq message arrived on closed channel` (kernel
  channels closing under a live notebook), `Notebook <PROJECT>/<file>.ipynb is not trusted` (notebook trust, mostly
  noise), `Replacing stale connection`.
- **frontend.log:** `Caught exception: [object Object]` from `d.logger.$exceptionHandler` is a browser-side JavaScript
  exception with no detail in the log. `Failed to select a pane for slug`, `Used deprecated remainingHeight` and
  `New icon mapping used without size` are UI noise.
- **install.log:** `WARNING: Use "yarn jar" to launch YARN applications.` repeats and is noise. Real failures show as
  `ERROR:root:Failed to migrate ...`, a `Traceback (most recent call last):`, or a database error such as
  `permission denied for schema ...`. Check which installer run (banner) the line belongs to: an old upgrade's failure
  may be long fixed.
- **codeenv:** `WARNING: Retrying (Retry(total=N ...)) after connection broken by ...` repeats per package and points
  at the package index or proxy being unreachable or slow. `error: subprocess-exited-with-error` /
  `metadata-generation-failed` / `Command errored out` is a package that failed to build; the `ERROR:` and `note:`
  lines just after name it. `ResolutionImpossible` and `No matching distribution found` are version conflicts or a
  package missing from the index.
- **dmesg:** `Memory cgroup out of memory: Killed process N (<name>)` and `oom-kill:constraint=CONSTRAINT_MEMCG`
  are cgroup OOM kills; the `task_memcg=` path names the responsible project and activity. `Call Trace:` follows
  the kernel reporting the fault.
- **eventserver.log:** had no WARN/ERROR at all in the design sample; a clean eventserver is normal.

## Masking and what is safe to quote

Log lines carry user names (`user=...`), email addresses, client IPs, project keys, scenario and dataset ids, URL
hosts, licence file names and request paths. The reader's other tools print counts only. `logscan.py` excerpts
replace these with `<user>`, `<email>`, `<ip>`, `<host>`, `<project>`, `<id>`, `<licence>`, `<secret>`,
`<cgroup>`. This is best effort: a project key written in an unusual place can survive, so a person must look at an
excerpt before it leaves the machine. Patterns are masked the same way and are the safe thing to quote. The
`first_seen_at` pointer (`run/backend.log:48213`) is a bundle path and a line number, never log text, so a reader can
open the original line.

## Gaps

- Job and scenario run logs, `timelines/` and `audit/audit.log.N` are not mirrored as content (see `limitations.md`);
  only the logs above are scanned.
- Compressed rotations (`.gz`, `.zip`) are not read; `gz_files_skipped` counts them.
- Format notes are from design and automation samples. `deployer` nodes are unverified.
