---
name: "dataiku-diagnosis-reader"
description: "Navigate and interpret an extracted Dataiku DSS diagnosis.zip support bundle (also: DSS diagnostic export, a folder named dku_diagnosis_*) to answer troubleshooting questions on instance configuration, crashes/OOMs, performance, users, connections, projects, code environments, plugins and logs, without re-deriving the bundle layout. Use whenever the user provides or asks about a Dataiku diagnosis bundle."
version: 0.24.0
---

# Dataiku DSS diagnosis.zip reader

A `diagnosis.zip` is DSS's built-in self-diagnostic export (run via `dssadmin diagnosis` or the
Administration UI). It is **not** a full backup — it's a curated mix of OS command captures, a
partial copy of the DSS data directory (`DATA_DIR`), and metadata-only file listings of the rest.
This skill tells you what's where, so you can route a question straight to the right file.

## The 3-tier content model

Every bundle mixes three kinds of content. Knowing which tier a file belongs to tells you whether
you're looking at real content or just a path/size record:

1. **OS/host diagnostic command outputs** — flat `.txt` files at the bundle root, each the
   captured stdout of one shell command (`uname -a`, `ps auxf`, `free -m`, `sysctl -a`, ...).
   `diag.txt` inlines only the *smaller* commands' output; big-output commands (package listings,
   `dmesg`, `sysctl`, `ps auxf`, `find -ls` scans, the JVM stack dump) run but leave only a bare
   timestamp placeholder in `diag.txt` — their real output is in their own dedicated file only.
   `timings.txt` is the complete, authoritative ledger of every step (including the ones
   `diag.txt` stubs out) with start/end times — see `references/root-files.md` before assuming
   something is or isn't in `diag.txt`.
2. **Real, fully-copied files** from a curated subset of `DATA_DIR` — under a "data-dir mirror"
   directory (see below) — covering `install.ini`, `config/`, `code-envs/`, `run/` logs, etc.
3. **Metadata-only manifests** (`find -ls` output — path/size/owner/mtime, **no content**) of the
   rest of `DATA_DIR` and the install dir: `datadir_listing.txt`, `installdir_listing.txt`,
   `config_listing.txt`, `lib_listing.txt`, `code_envs_desc_listing.txt`. **Job run history,
   scenario run logs, dataset build timelines, and audit-log content are frequently *only*
   present here** — you can confirm they exist/their size/when they last changed, but you cannot
   read their content from the bundle. Say so plainly rather than guessing.

How completely each tier is populated varies by DSS version, site, and size limits — treat this
as a structural model, not a byte-identical layout guaranteed across every bundle.

## Investigation workflow

1. **Orient.** Run `scripts/orient.sh <bundle_root>`: node type, version, data-dir mirror path, biggest files, and which key
   troubleshooting files are present. If it can't run where the bundle is, see `references/orient-fallback.md`; don't skip it.
   The mirror is the parent directory of `install.ini` (see `references/data-dir-identity.md`).
2. **Identify the node.** `design` and `automation` internals are verified (`references/node-types.md` says what differs). Any
   other `nodetype` (e.g. `deployer`) is an **unverified gap**: apply the 3-tier model but inspect its subtrees directly rather
   than assuming parity.
3. **Key settings in one command.** For the usual configuration values (a checklist review, a health check), run
   `scripts/facts.py <bundle_root>` once and quote its output instead of re-reading `general-settings.json` by hand. It prints
   JSON, `{fact: {value, source}}`. A missing setting is `"value": "ABSENT"` (with what was searched), never `false` or `0`; an
   unreadable one is `"ERROR"`. It never prints secrets. It is read-only Python 3 stdlib; if it cannot run where the bundle is,
   read the same values with the references and say you did.
4. **Route the question** through `references/lookup-table.md` (or the table below for common cases).
5. **Never load a large manifest or log whole** (`datadir_listing.txt` alone runs from ~340MB to ~2.3GB; rotated `run/*.log.N`
   reach ~100MB). `grep`/`awk`/`wc -l` first; see `references/listings-and-manifests.md` and `references/limitations.md`.
6. **For job or scenario run history, dataset build timelines or audit content**, check up front whether it is Tier 3
   (listing-only) before promising an answer (`references/limitations.md`).

## Quick lookup (most common questions)

| Question | Where |
|---|---|
| DSS version / node type | `<mirror>/dss-version.json`, `<mirror>/install.ini`, or `diag.txt` → `printenv`'s `DKU_NODE_TYPE` (fastest) |
| Any general OS question (CPU, memory, disk, env vars, JVM heap/ports) | `diag.txt` (small commands are inlined; `printenv` holds `DKU_*_JAVA_OPTS`/`DKU_*_PORT`); see `references/root-files.md` |
| Backend crash / OOM | `dmesg.txt` + `<mirror>/run/hs_err_pid*.log` + `cgroups_usage.txt` |
| Instance config (LDAP/SSO/proxy/concurrency/resources/internal DB) | `<mirror>/config/general-settings.json`; see `references/data-dir-config.md` |
| Users / connections / projects | `<mirror>/config/users.json`, `connections.json`, `projects/<KEY>/` |
| Backend/API/job execution trace, DSS self-diagnostics | `<mirror>/run/backend.log*`, `<mirror>/run/sanity-check.json` |
| Job/scenario run history, audit content | Usually **not in the bundle**: check `datadir_listing.txt` for existence/size only |

See `references/lookup-table.md` for the full index.

## Handling secrets

Bundles and files beside them hold live credentials (`general-settings.json` internal-DB, connection
and LDAP bind passwords; `connections.json`; `install.ini`; `dip.properties`; loose notes files). Tool
output lands in the transcript.

- Read only files you need; don't open notes or READMEs next to the bundle unless asked.
- **Open any config JSON with `scripts/peek.py <file> [--path a.b.c] [--depth N]`.** It prints the
  structure (keys, types, non-secret values) and masks passwords, tokens, keys and embedded
  credentials. Use it first to learn a file's shape; then `--path` to one key. For `.ini`/`.properties`,
  grep exact key names. A file has more than 40 keys at some level (`general-settings.json` has over
  100 at the top)? Add `--keys` (names only) or `--max-items 200`; don't fall back to a raw dump.
- **Deployer API key:** `general-settings.json` → `deployerClientSettings` holds one. Don't open that block raw: take `mode` and the
  target host from `facts.py` (`deployer`), or use `peek.py --path deployerClientSettings`, which masks the key.
- Never `cat`, `jq .`, or `print(json.load(...))` whole `general-settings.json`, `connections.json`,
  `users.json`, `install.ini` or `dip.properties`; never run `printenv`/`env` or read user scripts in
  full. Never dump a whole settings block or connection.
- Don't open user project code to look for keys: a scenario or recipe script can hold a literal API key
  in its first lines, and `head`/`cat`/`sed -n` prints it. Count instead:
  `grep -rlE "DSSClient\([^)]*[\"'][A-Za-z0-9_-]{20,}[\"']" <mirror>/config/projects/*/scenarios/ | wc -l`
  (`-l` lists file names only; `-c` counts). Report file names and counts, never the matching lines.
- Never print a whole sub-object (`json.dumps(settings["deployerClientSettings"])`, a truncated
  `str(block)[:200]`): encrypted `e:AES:` blobs and keys sit inside them. Use `peek.py --path`, or print
  named non-secret leaves only. Don't print a secret's length or prefix either.
- Don't list or print customer-internal metadata you don't need (the full connection list, hostnames, proxy
  details, `install.ini`): summarise in code (counts, names of the few items that matter) before printing.
- Never copy a secret into findings, notes, reports or decks.
- If one is printed, say so, name the file, and tell the user to rotate it.

## Reference index

- `references/root-files.md` — the command sequence (via `timings.txt`), what `diag.txt` inlines vs. stubs, an OS/system/environment
  table, and a per-file deep dive on every standalone root `.txt` file with ready-to-run grep patterns.
- `references/listings-and-manifests.md` — safely querying the `find -ls` manifests.
- `references/orient-fallback.md` — orienting when `orient.sh` can't run where the bundle is.
- `references/data-dir-identity.md` — finding the data-dir mirror; `install.ini` and `dss-version.json` fields.
- `references/node-types.md` — `design` vs. `automation` (verified); `deployer` and others (unverified).
- `references/data-dir-config.md` — the `config/` metastore, `projects/<KEY>/`, resource governance (cgroups, containers, K8s,
  Spark) and identifying the internal database.
- `references/data-dir-runtime-and-codeenvs.md` — `run/` logs, `code-envs/`/`acode-envs/`, `install-support/`, `plugins/dev/`.
- `references/logs.md` — per-log line formats, error signatures, masking, and `scripts/logscan.py` (errors and warnings of every major log, grouped; signature-first; `--since/--until/--around` and `--timeline` to narrow to an incident).
- `references/lookup-table.md` — the full "where do I find X" index.
- `references/limitations.md` — verified scope, known content gaps, large-file hazards.
