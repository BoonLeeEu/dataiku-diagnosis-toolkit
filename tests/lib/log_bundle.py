"""A synthetic bundle carrying every log logscan.py reads, built into a temp directory by the tests.

SYNTHETIC TEST FIXTURE - not real diagnosis data. Every name, address and secret below is invented. The values in
LEAKS are planted in the logs on purpose: a masked report must never contain any of them.
"""
import gzip
from pathlib import Path

# Planted identifying values; no output of logscan.py may contain any of them.
LEAKS = ["jane.doe@example.org", "10.20.30.40", "alice_analyst", "ACMESALES", "hunter2-secret", "License-jane.doe",
         "db-prod-01.example.org", "e:AES:QWxhZGRpbjpvcGVu"]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(root: Path, *, without: tuple = ()) -> Path:
    """Write the bundle under `root`; `without` lists run/ file names (or root files) to leave out. Returns `root`."""
    def put(rel, text):
        if Path(rel).name not in without:
            write(root / rel, text)

    m = root / "data_dataiku" / "design"
    write(m / "install.ini", "[general]\nnodeid = synthetic-design-01\nnodetype = design\n")
    r = "data_dataiku/design/run/"

    put(r + "backend.log.1",
        "[2026/01/01-00:00:01.000] [main] [INFO] [dku.startup]  - DSS backend starting\n"
        "[2026/01/01-01:00:00.000] [jek-1] [ERROR] [dku.jobs.exec]  - Job 'build_ACMESALES.sales' failed: heap\n"
        "\tat com.dataiku.dip.Foo.run(Foo.java:10)\n")
    put(r + "backend.log",
        "[2026/01/03-00:00:00.000] [main] [INFO] [dku.startup]  - DSS backend restarted\n"
        "[2026/01/03-01:00:00.000] [jek-2] [ERROR] [dku.jobs.exec]  - Job 'build_ACMESALES.orders' failed: heap\n"
        "[2026/01/03-01:02:00.000] [kern-1] [ERROR] [dku.kernels]  - Kernel crashed\n"
        "java.lang.IllegalStateException: no memory\n"
        "\tat com.dataiku.dip.Foo.run(Foo.java:10)\n"
        "Caused by: java.lang.OutOfMemoryError: Java heap space\n"
        "[2026/01/03-01:03:00.000] [jek-4] [INFO] [dku.jobs]  - Task died: java.lang.OutOfMemoryError: Java heap space\n"
        "[2026/01/03-01:05:00.000] [jek-3] [ERROR] [dku.jobs.exec]  - Job 'build_ACMESALES.items' failed: heap\n"
        "[2026/01/03-01:10:00.000] [jek-3] [INFO] [dku.jobs.exec]  - subprocess said [ERROR] nothing\n"
        "[2026/01/03-02:00:00.000] [t-1] [WARN] [dku.tracing]  - Slow call user=alice_analyst from 10.20.30.40\n"
        "[2026/01/03-03:00:00.000] [t-2] [ERROR] [dku.auth]  - Login failed for jane.doe@example.org"
        " password=hunter2-secret\n"
        "[2026/01/03-04:00:00.000] [sched-1] [ERROR] [dku.scenarios]  - Cannot run scenario ACMESALES.NIGHTLY:"
        " configured to run as user 'alice_analyst' which does not exist\n")
    if "backend.log.2.gz" not in without:
        with gzip.open(root / r / "backend.log.2.gz", "wb") as fh:
            fh.write(b"[2025/12/01-00:00:00.000] [main] [ERROR] [x]  - old\n")

    put(r + "frontend.log.0",
        "[2026/01/03-00:00:00] [sess-a] [DEBUG] [d.s.API]  - [S] GET /dip/api/x\n"
        "[2026/01/03-00:00:01] [sess-a] [ERROR] [d.logger.$exceptionHandler]  - Caught exception: [object Object] \n"
        "[2026/01/03-00:00:02] [sess-a] [WARN] [d.dirs.styling]  - Used deprecated remainingHeight on [object Object]\n")
    put(r + "frontend.log.1",
        "[2026/01/02-00:00:01] [sess-b] [ERROR] [d.logger.$exceptionHandler]  - Caught exception: [object Object] \n")

    put(r + "nginx.log",
        'nginx: [alert] could not open error log file: open() "/var/log/nginx/error.log" failed (13: Permission denied)\n'
        '2026/01/03 04:00:00 [error] 11#11: *1 connect() failed (111: Connection refused) while connecting to upstream,'
        ' client: 10.20.30.40, server: , request: "GET /x HTTP/1.1", upstream: "http://127.0.0.1:11200/x", host: "db-prod-01.example.org"\n'
        '2026/01/03 04:00:01 [error] 11#11: *2 connect() failed (111: Connection refused) while connecting to upstream,'
        ' client: 10.20.30.41, server: , request: "GET /y HTTP/1.1"\n'
        '2026/01/03 04:00:02 [emerg] 11#11: cannot load certificate key "/etc/ssl/key.pem": BIO_new_file() failed\n')

    put(r + "ipython.log",
        "[2026/01/03-00:00:00.000] [100/MainThread] [INFO] [NotebookApp] [dku_call_id=a]  Start call: /x user=alice_analyst\n"
        "[2026/01/03-00:00:01.000] [100/MainThread] [WARNING] [NotebookApp] [dku_call_id=b]  zmq message arrived on closed channel\n"
        "[2026/01/03-00:00:02.000] [100/MainThread] [ERROR] [NotebookApp] [dku_call_id=c]  Uncaught exception in ZMQStream callback\n")

    put(r + "eventserver.log",
        "Loading plugins: ,model-error-analysis\n"
        "[2026/01/03-00:00:00.000] [main] [INFO] [dku.logging]  - Loading logging settings\n")

    put(r + "supervisord.log",
        "2026-01-03 05:00:00,000 INFO supervisord started\n"
        "2026-01-03 05:00:01,000 WARN killing 'nginx' (123) with SIGKILL\n"
        "2026-01-03 05:00:02,000 INFO exited: backend (exit status 1; not expected)\n"
        "2026-01-03 05:00:03,000 INFO gave up: backend entered FATAL state, too many start retries too quickly\n")

    put(r + "install.log",
        "*********************************************************\n"
        "Data Science Studio installer: 2025/06/16-11:24:53\n"
        "Command line: ./installer.sh -d /data/dss -l License-jane.doe@example.org-2026.json -p 10000\n"
        "[2025/06/16-11:25:00.000] [main] [INFO] [dku.install]  - Installing\n"
        "ERROR:root:Failed to migrate perf /data/dss/analysis-data/ACMESALES/abc\n"
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in <module>\n'
        "org.postgresql.util.PSQLException: ERROR: permission denied for schema dss_design_data\n"
        'WARNING: Use "yarn jar" to launch YARN applications.\n')
    put(r + "install-impersonation.log",
        "*********************************************************\nData Science Studio admin tool: 2025/06/26\n"
        "[2025/06/26-11:40:08.000] [main] [INFO] [dku.admin]  - done\n")

    put("data_dataiku/design/code-envs/logs/python/env1/createPythonEnv.log",
        "Collecting numpy\n"
        "WARNING: Retrying (Retry(total=4, connect=None)) after connection broken by 'ConnectTimeoutError'\n"
        "ERROR: Could not find a version that satisfies the requirement foo==9.9\n"
        "ERROR: No matching distribution found for foo==9.9\n"
        "Fetching from https://user:e:AES:QWxhZGRpbjpvcGVu@db-prod-01.example.org/simple\n")

    put("dmesg.txt",
        "[    0.000000] Linux version 5.14.0 (synthetic)\n"
        "[86012.123456] java invoked oom-killer: gfp_mask=0x140cca, order=0\n"
        "[86012.123999] Memory cgroup out of memory: Killed process 4242 (java) total-vm:9000000kB, anon-rss:7900000kB\n"
        "[90000.000000] INFO: task jbd2/sda1-8:481 blocked for more than 120 seconds.\n")
    put("stacks.txt",
        '"qtp-1" #20 prio=5 os_prio=0 tid=0x1 nid=0x2 waiting for monitor entry\n'
        "   java.lang.Thread.State: BLOCKED (on object monitor)\n"
        "\tat com.dataiku.Foo.bar(Foo.java:1)\n"
        '"main" #1 prio=5\n   java.lang.Thread.State: RUNNABLE\n'
        "Found one Java-level deadlock:\n=============================\n")
    put(r + "hs_err_pid4242.log",
        "#\n# There is insufficient memory for the Java Runtime Environment to continue.\n"
        "# Native memory allocation (mmap) failed to map 1048576 bytes for committing reserved memory.\n"
        "# Out of Memory Error (os_linux.cpp:2749), pid=4242\n#\n"
        "Time: Sat Jan  3 01:00:00 2026 UTC elapsed time: 100 seconds\n"
        "java_command: com.dataiku.dip.DSSBackendMain\n")
    return root
