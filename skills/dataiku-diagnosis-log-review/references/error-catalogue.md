# Error catalogue

Known log signatures, what each most likely means, and what to do. Entries come from the signatures seen in real design
and automation bundles plus well-known DSS behaviour. This is judgment, not layout: how a log is laid out is the
reader's `references/logs.md`.

**How to use it.** Match a finding's pattern to an entry's *Signature*. Apply the entry's *Confidence* rule and never
rate higher. A finding no entry covers is judged from its excerpt, and is `Unknown` unless the text itself states the
cause. Setting names and commands below are as in recent DSS releases; before giving a step that edits a setting or
runs a command, confirm it for the bundle's product version in the Dataiku documentation, and say so in the step when
you could not. A step that restarts DSS or needs a maintenance window says so.

Entry ids are stable (`LOG-<area>-<nnn>`); cite them in `notes` (e.g. "catalogue LOG-OOM-001").

## Memory and crashes

### LOG-OOM-001 Java heap exhausted
- **Signature:** `OutOfMemoryError: Java heap space` (or `GC overhead limit exceeded`) in the backend log or a crash dump's header; a count that rises with job activity.
- **Cause:** The JVM named in the finding (the backend, a job process, a notebook kernel) hit its configured maximum heap. Either the heap is too small for the workload, a single operation holds too much in memory, or too many jobs ran at once in one JVM.
- **Confidence:** `Confirmed` when the message names the heap and the process is identifiable (excerpt, or the JVM crash dump's main class). `Likely` when the process is not identifiable. Never state the right heap size: that needs the host's memory and the workload.
- **Check next:** Which process (the thread or class in the excerpt; the crash dump's main class). The configured heap for that process against the host's RAM (reader `facts.py`). Concurrent jobs and scenarios around `first_seen_at` (the log's window). Whether the same time shows a kernel OOM kill (LOG-OOM-002).
- **Mitigation:**
  1. Identify the process from the excerpt before changing anything.
  2. Check the host has headroom: the sum of all DSS process heaps plus job memory must fit in RAM. Do not raise a heap on a host that is already near its limit.
  3. Raise that process's maximum heap in the install configuration (for the backend, the backend Xmx setting), apply it with `dssadmin regenerate-config`, then restart DSS (a maintenance window).
  4. If one job or recipe is the trigger, reduce its memory use (stream instead of loading, sample, partition) or move it to containerised execution so it has its own memory limit.
  5. Re-check the log after a few days of normal load.

### LOG-OOM-002 Kernel out-of-memory kill
- **Signature:** `Out of memory: Killed process <pid> (<name>)`, `Memory cgroup out of memory`, `oom-kill:constraint=...`, `invoked oom-killer` in the kernel log.
- **Cause:** The Linux kernel killed a process because the host (constraint `NONE`) or a cgroup (constraint `MEMCG`) ran out of memory. DSS processes and job processes are common victims.
- **Confidence:** `Confirmed` that a process was killed for memory. The cause of the pressure is `Likely` until the process name, the cgroup path (it names the project and activity) and the memory limit are known; the cgroup path in a raw line is masked, so point at `first_seen_at`.
- **Check next:** The killed process's name and RSS at kill time (excerpt). Whether the constraint is a cgroup limit or the whole host. The project/activity named by the cgroup path (open `first_seen_at`). Whether DSS resource control (cgroups) is enabled and what limit it sets (reader `facts.py`). A matching crash or restart in the process-manager log (LOG-SUP-001).
- **Mitigation:**
  1. If the constraint is a cgroup limit: decide whether the limit is too low for the activity or the activity is using too much; raise the limit in DSS resource control, or reduce the activity's memory (partition, sample, a lighter recipe engine).
  2. If the constraint is the host: add RAM or swap, lower concurrent job limits, or move heavy activities to containerised execution (Kubernetes) so they cannot starve the node.
  3. If the killed process was a DSS service (backend, a job process), see LOG-OOM-001 and LOG-SUP-001: it will have restarted.
  4. Record the kill times; repeated kills of the same process at a regular time point to a scheduled scenario.

### LOG-JVM-001 JVM crash: insufficient native memory
- **Signature:** A crash dump with `There is insufficient memory for the Java Runtime Environment to continue` or `Native memory allocation (mmap) failed`; problem class `Out of Memory Error`.
- **Cause:** The JVM could not get native (non-heap) memory from the OS: the host, or its cgroup, was out of RAM and swap. This is not a Java heap error.
- **Confidence:** `Confirmed` for what the dump says. The reason the host was out of memory is `Likely` the same pressure as a kernel OOM kill at that time (LOG-OOM-002); say `Unknown` for that part if there is no matching kernel finding.
- **Check next:** The dump's `Time` against the process-manager log and any kernel OOM finding. The process (the dump's main class). Free memory and swap on the host (reader root-file notes), and whether other services share the host.
- **Mitigation:**
  1. Treat it as host or cgroup memory pressure, not a heap setting: follow LOG-OOM-002 steps 1 and 2.
  2. Do not simply raise the JVM heap; that raises native memory demand and can make this worse.
  3. After the cause is addressed, confirm the process restarted cleanly (LOG-SUP-001).

### LOG-JVM-002 JVM crash: internal error or signal
- **Signature:** A crash dump with problem class `Internal Error` or `SIGSEGV`/`SIGBUS`.
- **Cause:** A fault inside the JVM or a native library, not a memory shortage. Often a JVM or native-library bug, a corrupted file, or failing hardware.
- **Confidence:** `Unknown` for the cause unless the dump's first lines name it. `Confirmed` only that the JVM crashed.
- **Check next:** The dump's problem frame (the header names the library or function; open the crash dump header, not the whole file). The JVM version and DSS version (reader `facts.py`). Whether it recurs at the same point. Kernel messages at that time (a segfault or I/O error, LOG-KRN-001).
- **Mitigation:**
  1. Capture the crash dump and the DSS version and open a Dataiku support case if it recurs; native crashes are not fixed by configuration.
  2. Check the host for hardware or filesystem errors in the kernel log.
  3. Check that the JVM in use is one DSS supports for this version.

### LOG-SUP-001 A DSS process keeps exiting or gives up restarting
- **Signature:** In the process-manager log: `exited: <process> (exit status N; not expected)`, `exited: ... (terminated by SIGABRT (core dumped); not expected)`, `gave up: <process> entered FATAL state, too many start retries too quickly`.
- **Cause:** The process crashed and the process manager restarted it. After repeated quick failures it stops trying and the service stays down. The log line says nothing about why the process died.
- **Confidence:** `Confirmed` that the process crashed or stopped restarting. The cause is `Likely` when a kernel OOM kill (LOG-OOM-002) or JVM crash dump (LOG-JVM-001/002) fits the same time and process; otherwise `Unknown`.
- **Check next:** The process's own log just before the exit (open the finding's `first_seen_at` neighbours in that log: a gap or an abrupt end is itself evidence). A crash dump or kernel OOM finding at the same time. Disk-full or permission messages in the install or startup logs. Whether a start failed on a port already in use or on a bad configuration after an upgrade.
- **Mitigation:**
  1. Find the cause in the process's own log and the kernel log before restarting repeatedly.
  2. If the process is in FATAL state (not running), fix the cause, then start it again with the DSS control command (`dss restart`, or the process-manager control for that process) in a maintenance window.
  3. For a SIGABRT of a Java process, treat as LOG-JVM-001/002 by its crash dump.
  4. Note the exit count and window; many exits clustered around restarts or deployments are expected, steady ones are not.

### LOG-SUP-002 Process killed with SIGKILL at stop
- **Signature:** `killing '<process>' (<pid>) with SIGKILL` (WARN) in the process-manager log.
- **Cause:** The process did not exit within the time allowed after a stop request, so it was forcibly killed. Usually during a restart, upgrade or shutdown.
- **Confidence:** `Likely` benign when each occurrence falls next to a restart or stop (`received SIGTERM`, `stopped`). `Unknown` if it happens with no stop request.
- **Check next:** Whether each one follows a stop or restart request in the same log. Whether it is always the same process (a slow-stopping notebook server or proxy).
- **Mitigation:**
  1. If only at restarts: no action needed.
  2. If always the same process, check why it is slow to stop (long-running work, hung connections) and restart it cleanly outside peak hours.

## Reverse proxy (nginx)

### LOG-NGX-001 Upstream connection refused
- **Signature:** `connect() failed (111: Connection refused) while connecting to upstream`.
- **Cause:** The proxy could not reach the DSS backend (or another service) because nothing was listening: it was down, restarting, or not yet started. Users see 502 errors during that time.
- **Confidence:** `Likely` that the backend was unavailable during the window. `Confirmed` when a backend exit or restart (LOG-SUP-001, a gap in the backend log) covers the same time.
- **Check next:** The window of the finding against the process-manager and backend logs. Whether it clusters at restarts or runs continuously (continuous means the backend is down or listening on another port).
- **Mitigation:**
  1. Find why the backend was down: LOG-SUP-001, LOG-OOM-001/002.
  2. If it is only at restarts, schedule restarts outside business hours and tell users.
  3. If continuous, confirm the backend is running and its port matches the proxy's upstream configuration.

### LOG-NGX-002 Upstream timed out or closed early
- **Signature:** `upstream timed out`, `upstream prematurely closed connection while reading response header`.
- **Cause:** The backend did not answer in time, or died mid-response: it was overloaded, in a long garbage collection, or crashed.
- **Confidence:** `Likely`. `Confirmed` only if a backend crash or OOM finding covers the same window.
- **Check next:** Backend errors, OOM and slow-call warnings in the same window. The request path in the excerpt (a slow endpoint vs everything). Host CPU and memory at that time.
- **Mitigation:**
  1. Fix the backend's overload or crash first (LOG-OOM-001, LOG-SUP-001).
  2. If one endpoint is slow, investigate that endpoint rather than raising proxy timeouts.
  3. Raise proxy timeouts only if long requests are legitimate; that hides, not fixes, a slow backend.

### LOG-NGX-003 Not-found noise and scanner probes
- **Signature:** `open() "<path>" failed (2: No such file or directory)`, `"<path>" is not found`, `directory index of "<path>" is forbidden`; paths such as `.well-known`, `cgi-bin`, `${...}` or script payloads.
- **Cause:** Requests for files DSS does not serve: stale bookmarks, browsers asking for icons, or automated vulnerability scanners probing the host. Usually the largest error count in the proxy log.
- **Confidence:** `Confirmed` that it is not a DSS fault. If the paths look like attack payloads, say they are probes and that the host is reachable from a scanning network.
- **Check next:** Whether the paths are payload-like (probing) or genuine DSS routes (a broken link or plugin). Whether the host should be reachable from the sources scanning it (the addresses are masked).
- **Mitigation:**
  1. No DSS action needed for the errors themselves.
  2. If the paths are probes, confirm the node is not exposed to the public internet; put it behind a VPN, WAF or allowlist if it should not be.
  3. If a genuine DSS route returns not-found, check that the plugin or webapp it belongs to is installed and enabled.

### LOG-NGX-004 Cannot load certificate or key
- **Signature:** `cannot load certificate "<path>"` or `cannot load certificate key "<path>"`, e.g. `BIO_new_file() failed ... No such file`.
- **Cause:** HTTPS is configured but the proxy cannot read the certificate or key file: the path is wrong, the file is missing, or the DSS user has no permission. The proxy cannot start with HTTPS.
- **Confidence:** `Confirmed`: the message states it.
- **Check next:** That the configured certificate and key paths exist and are readable by the DSS user (reader `facts.py` reports whether HTTPS is on and the certificate paths as yes/no). Whether a recent certificate renewal moved the files.
- **Mitigation:**
  1. Correct the certificate and key paths in the DSS HTTPS configuration, or restore the files.
  2. Make them readable by the DSS user (and the key unreadable by others).
  3. Regenerate the proxy configuration (`dssadmin regenerate-config`) and restart DSS (a maintenance window).
  4. Confirm HTTPS answers afterwards.

### LOG-NGX-005 Proxy cannot open its default error log
- **Signature:** `nginx: [alert] could not open error log file: open() "/var/log/nginx/error.log" failed (13: Permission denied)`, repeated at each start.
- **Cause:** The proxy binary tries to open a compiled-in default log path that the DSS user cannot write, then falls back to the log DSS configured. A start-up message with no effect on service.
- **Confidence:** `Likely` benign: it has no timestamp and appears once per start.
- **Check next:** That the proxy otherwise runs (later lines in the same log show real requests being logged).
- **Mitigation:**
  1. No action needed.
  2. Optional: make the default path writable or ignore the line in monitoring.

## Notebooks (ipython)

### LOG-IPY-001 Notebook channel errors
- **Signature:** `Uncaught exception in ZMQStream callback` / `zmqstream callback`, `zmq message arrived on closed channel`, `Replacing stale connection`.
- **Cause:** A notebook kernel's channel closed while a client was still attached: the kernel was killed, restarted or idled out, or the browser tab went away. Common and mostly harmless.
- **Confidence:** `Likely` benign when counts are steady and kernels are otherwise started and used. `Unknown` if they coincide with a spike or users reporting lost notebook sessions.
- **Check next:** Whether the same time shows kernels being killed in the backend log (idle culling, memory kill, user shutdown). Whether users report notebooks dying.
- **Mitigation:**
  1. If steady and unreported: no action.
  2. If kernels are dying under memory pressure, follow LOG-OOM-002.
  3. If kernels are culled when users expect them to persist, review the idle-kernel timeout in the notebook settings.

### LOG-IPY-002 Notebook server rejects requests: failed to authenticate
- **Signature:** `Failed to authenticate request` from the notebook server.
- **Cause:** Requests to the notebook server arrived without a valid session or API ticket: an expired browser session, a stale notebook tab, a client or integration with a bad token, or probing.
- **Confidence:** `Unknown` unless the excerpt shows the cause. `Likely` expired sessions when the count is low and spread out.
- **Check next:** Counts over the window (a burst vs steady). The matching authentication failures in the backend log. Whether any integration (an IDE plugin, a Code Studio, an external client) uses the notebook server directly.
- **Mitigation:**
  1. Ask the affected users to reload and sign in again; this clears stale sessions.
  2. If bursts repeat from one source, find the client and fix or remove its credentials; if the source is unknown, treat it as probing and restrict network access.
  3. Escalate if it follows a DSS upgrade or an authentication change (SSO).

### LOG-IPY-003 Notebook is not trusted
- **Signature:** `Notebook <project>/<name>.ipynb is not trusted`.
- **Cause:** Jupyter's trust mechanism flags a notebook not signed by the current server. Informational.
- **Confidence:** `Confirmed` noise.
- **Check next:** None.
- **Mitigation:**
  1. No action needed.

## Backend

### LOG-BE-001 WebSocket connection rejected: could not authenticate
- **Signature:** `WS connection from <ip>:<port> rejected (could not authenticate)`.
- **Cause:** A browser's live-update connection arrived without valid credentials: an expired session in an open tab, a proxy that does not forward the authentication, or a client that never signed in.
- **Confidence:** `Likely` expired sessions when the count is steady and low per user. `Unknown` for a high or bursty count.
- **Check next:** Counts over the window. Whether the source addresses are the proxy or load balancer (if every connection comes from one address, the proxy may not forward the real client or the cookie). The authentication configuration for SSO sessions.
- **Mitigation:**
  1. If it is open tabs after session expiry: no action; reload the page.
  2. If every rejection comes from the proxy's address, check that the proxy forwards the WebSocket upgrade and cookies.
  3. If bursty from one address, check for a misconfigured client or a probe.

### LOG-BE-002 Public API call failed
- **Signature:** `API call '<name>' failed` from the public API logger.
- **Cause:** Some call through the public API (a script, an integration, a scenario step) returned an error. The pattern is generic: the real cause is in the excerpt's exception.
- **Confidence:** `Unknown`, unless the excerpt's exception names the cause (then follow its message).
- **Check next:** Open `first_seen_at` for the exception and the endpoint. The caller (a user or integration; the name is masked). Whether the failures are one project or one API call.
- **Mitigation:**
  1. Read the exception in the log at `first_seen_at` and fix its stated cause (permissions, a missing object, invalid input).
  2. If a scheduled integration is the caller, fix it at the source and re-run.

### LOG-BE-003 Scenario run failed
- **Signature:** `scenario <project>.<id> - Step run hard failure` and nearby scenario warnings.
- **Cause:** A step of a scenario failed hard. The pattern is the same for any scenario; the reason (a failed build, a missing dataset, a mail or query failure) is in the lines around it.
- **Confidence:** `Unknown` for the reason. `Confirmed` only that the scenario failed.
- **Check next:** The scenario's own run history in the project (the bundle holds no scenario run logs). The step and its error at `first_seen_at`. Whether the failures repeat on a schedule.
- **Mitigation:**
  1. Open the scenario's last runs in the project and read the failed step's log.
  2. Fix the step's stated cause, then re-run.
  3. If failures are expected during maintenance, add the scenario to the exclusions or pause its trigger.

### LOG-BE-004 Scenario set to run as a user that no longer exists
- **Signature:** `Cannot run scenario <project>.<id>: configured to run as user '<name>' which does not exist`.
- **Cause:** A scenario's "Run as" user was deleted. The scenario's triggers are skipped every time the trigger list is rebuilt, so one scenario can produce thousands of lines.
- **Confidence:** `Confirmed`: the message states it.
- **Check next:** The affected scenarios (the finding's pattern names the project). Whether the scenario is still wanted.
- **Mitigation:**
  1. Open each affected scenario and set "Run as" to an existing user with the right permissions, or reassign the scenario's owner.
  2. If the scenario is obsolete, delete or deactivate it.
  3. Before deleting a user, reassign or deactivate the scenarios that run as them.

### LOG-BE-005 Audit message dispatch failed
- **Signature:** `Failed dispatching audit message to <dispatcher class>`.
- **Cause:** An audit target (the event server, a log appender, an external sink) did not accept messages. Audit events may be lost for the affected target.
- **Confidence:** `Unknown` for which target and why; `Likely` the target is unreachable if the event server shows errors or restarts at the same time.
- **Check next:** The dispatcher class in the excerpt. The event-server log and the process-manager log for the same window. The audit target configuration (the sanity checks may already flag a missing target).
- **Mitigation:**
  1. Identify the failing target from the class name.
  2. Restore the event server or fix the target's configuration or connectivity.
  3. If audit completeness matters for compliance, note the gap window.

## Frontend

### LOG-FE-001 Browser-side exception
- **Signature:** `Caught exception: [object Object]` from the exception handler.
- **Cause:** A JavaScript exception in some user's browser session. The log records no detail, so the cause cannot be read from it.
- **Confidence:** `Unknown`; usually harmless UI noise unless users report broken pages.
- **Check next:** Whether the count spikes after an upgrade or plugin install. Whether users report a specific page failing. Backend errors in the same window for a matching failed API call.
- **Mitigation:**
  1. If users report no problem: no action.
  2. If a page is broken, reproduce it with the browser's developer console open to get the real exception, and report that.
  3. Check that browsers and any custom plugin or webapp code are current.

### LOG-FE-002 UI deprecation and layout warnings
- **Signature:** `Used deprecated remainingHeight`, `Failed to select a pane for slug`, `New icon mapping used without size`, `flush old local dss history`.
- **Cause:** The UI warning about its own deprecated or optional behaviour. Informational.
- **Confidence:** `Confirmed` noise.
- **Check next:** None.
- **Mitigation:**
  1. No action needed. Report to Dataiku support only if it persists after an upgrade and degrades the UI.

## Installation and upgrade

### LOG-INST-001 Internal database permission denied during install or upgrade
- **Signature:** `PSQLException: ERROR: permission denied for schema <name>` (also failed `CREATE`/`ALTER`) in the install transcript.
- **Cause:** The database user DSS connects with lacked privileges on a schema during a migration step. Part of the upgrade or setup did not complete.
- **Confidence:** `Confirmed` that a migration step failed. Whether it is still unresolved is `Unknown`: the install transcript spans several installer runs; check which run (banner and date) the line belongs to.
- **Check next:** Which installer run the line belongs to. Whether DSS runs with the affected feature working today (the feature depending on that schema). The internal database configuration in the bundle (reader `facts.py` `internal_database`).
- **Mitigation:**
  1. Confirm the schema's owner and that the DSS database user has the required privileges (create and usage on the schema).
  2. Re-run the failed migration through the supported path for the version (restart DSS so it retries, or follow the upgrade notes); confirm in the DSS logs that the step now succeeds.
  3. If the failure is from an old, since-fixed run, record it as historical.

### LOG-INST-002 Migration failure for a specific item
- **Signature:** `Failed to migrate <thing> <path>` logged at error level by an upgrade helper script, with a Python traceback.
- **Cause:** An upgrade migration failed for one analysis, model or item (corrupted or missing data, an unexpected format). The upgrade continues; that item may be missing history or metrics.
- **Confidence:** `Unknown`. Confirmed only that the migration of those items failed at that run.
- **Check next:** The traceback at `first_seen_at`. Which run (date) and whether the item is still in use. Whether the items fail on every upgrade or once.
- **Mitigation:**
  1. Open the traceback for the stated error and check whether the item is still used.
  2. If unused, delete the item's stale data or ignore it.
  3. If used, restore it from a backup or rebuild it (retrain the model) and open a Dataiku support case with the traceback if the error is on current data.

### LOG-INST-003 Installer warnings that are noise
- **Signature:** `WARNING: Use "yarn jar" to launch YARN applications.`, `Spark is already enabled`, `Execution configs already exist, not overriding`.
- **Cause:** Installer and Hadoop-client chatter; informational.
- **Confidence:** `Confirmed` noise.
- **Check next:** None.
- **Mitigation:**
  1. No action needed.

## Code environments

### LOG-ENV-001 Package index unreachable or slow
- **Signature:** `WARNING: Retrying (Retry(total=N ...)) after connection broken by ...`, `Connection ... timed out`, `HTTP error N while getting https://<host>/...`.
- **Cause:** The package index or proxy DSS builds code environments from did not answer, answered slowly, or returned an error. Builds fail or take very long; the retry count is the symptom.
- **Confidence:** `Likely` for retries; `Confirmed` only that connections to the index failed. An `HTTP error N` points at an authentication, URL or repository fault at the index: `Unknown` until the status is known.
- **Check next:** The status code in `HTTP error N`. The index and proxy configured for the DSS host (outside the bundle; ask the platform team). Network access from the DSS host to the index. Whether builds that fail are all on one environment or all of them.
- **Mitigation:**
  1. Test reaching the package index from the DSS host with the same proxy and credentials DSS uses.
  2. Correct the index URL, proxy, certificate trust or credentials in the pip configuration DSS uses for code environments (see the Dataiku documentation on code environments for where for this version).
  3. Rebuild or update the failed environments.
  4. If the index is an internal mirror, check that it caches the needed packages.

### LOG-ENV-002 `sklearn` package name in an environment's requirements
- **Signature:** `Preparing metadata (setup.py): finished with status 'error'` together with `SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL` and `The 'sklearn' PyPI package is deprecated, use 'scikit-learn'`.
- **Cause:** The environment's requested packages list `sklearn`, a deprecated alias that no longer installs. The build of every such environment fails.
- **Confidence:** `Confirmed`: the message states it.
- **Check next:** Which environments list `sklearn` (the log's path names the environment).
- **Mitigation:**
  1. In each affected code environment, replace `sklearn` with `scikit-learn` in the requested packages.
  2. Update the environment so its packages are reinstalled.
  3. Do not set the allow-deprecated environment variable; it only delays the failure.

### LOG-ENV-003 Dependencies cannot be resolved
- **Signature:** `No matching distribution found for <pkg>`, `ResolutionImpossible`, `Could not find a version that satisfies the requirement`, `error: subprocess-exited-with-error`, `Failed building wheel`.
- **Cause:** The requested package or version does not exist in the index for this Python version, two requirements conflict, or a package that needs compiling lacks a compiler or system library.
- **Confidence:** `Likely` for the category; the exact package and reason are in the lines after the error. `Confirmed` when the message names the missing version or library.
- **Check next:** The package named in the log lines after `first_seen_at`. The environment's Python version. Whether the build host has the compiler or library it names.
- **Mitigation:**
  1. Open the environment's build log for the package and the reason.
  2. Fix the requirement: pin a version that exists for that Python version, relax a conflicting pin, or remove the package.
  3. For a compile failure, install the missing system library or compiler on the host, or use a wheel.
  4. Rebuild the environment.

## Kernel and threads

### LOG-KRN-001 Process crash or I/O fault in the kernel log
- **Signature:** `<process>[pid]: segfault at ...`, `general protection`, `I/O error`, `EXT4-fs error`, `XFS ... error`, `Call Trace:`.
- **Cause:** A process crashed on a bad memory access, or the storage layer reported errors. `Call Trace:` follows a kernel-reported fault.
- **Confidence:** `Unknown` for the cause. `Confirmed` only that a fault was logged.
- **Check next:** The process name in the excerpt. Whether a crash dump or process exit matches. Storage health on the host (the data directory's filesystem and disk), and a recent kernel or driver change.
- **Mitigation:**
  1. Identify whether the faulting process is DSS-related (backend, a job process) or unrelated.
  2. For I/O or filesystem errors, check the disk and filesystem health with the platform team; act before data loss.
  3. For a DSS process, see LOG-JVM-002 and LOG-SUP-001.

### LOG-KRN-002 Hung task or I/O stall
- **Signature:** `task <name> blocked for more than N seconds`, `hung_task`, `soft lockup`.
- **Cause:** A process waited too long on I/O or a lock: slow or stalled storage, an overloaded host, or a hung network filesystem.
- **Confidence:** `Likely` a storage or I/O stall when the process is a journalling or filesystem thread; otherwise `Unknown`.
- **Check next:** The blocked task's name. Whether the data directory is on network storage. Disk latency and host load at that time (cannot be read from the bundle).
- **Mitigation:**
  1. Check the storage for latency or errors with the platform team.
  2. If the data directory is on a network filesystem, check its health and mount options.
  3. Reduce I/O contention (concurrent jobs, backups at the same time).

### LOG-STK-001 Blocked threads or deadlock in the thread dump
- **Signature:** A thread in state `BLOCKED` in the thread dump; `Found one Java-level deadlock`.
- **Cause:** Threads were waiting on a lock held by another thread at dump time; a deadlock means they will wait forever. A few BLOCKED threads at one instant are normal; many on the same monitor, or a deadlock, are not.
- **Confidence:** `Unknown` unless the dump reports a deadlock (`Confirmed`). A single dump is a single instant.
- **Check next:** Which monitor many threads wait on (the dump names the lock and the holding thread). Whether the dump was taken during a slow period. Whether slow-call warnings in the backend log match the time.
- **Mitigation:**
  1. For a deadlock, restart the affected process in a maintenance window, and open a Dataiku support case with the dump.
  2. For many threads on one monitor, take two more dumps a minute apart to see whether the holder changes.
  3. Correlate with the slowest operations in the backend log.
