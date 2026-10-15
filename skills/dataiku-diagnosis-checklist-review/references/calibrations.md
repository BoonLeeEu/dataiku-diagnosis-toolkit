# Check-specific calibrations

> Judgment only: this file says which status to give and what to write, never where or how to find something in the
> bundle. That belongs to the reader (`dataiku-diagnosis-reader` skill), which is vendored from
> upstream. If a calibration needs a new "where/how to read" fact, add it to the reader's references
> upstream, re-sync, and point to it from here. See `CLAUDE.md`.

These interpretations come directly from the user and override a literal reading of a checklist's
`expected_value`/evidence text. **Match an entry by what the check is about (its title and statement).**
The ids cited here point into the bundled default checklist; a different or newer checklist may renumber,
split, merge or drop checks. If a row's id and title disagree with an entry (anchor titles:
`tests/calibration_anchors.md`), trust the topic, not the id, and say so in `notes`. Add each new entry under
the right heading; don't overwrite prior ones.

**Two kinds of check.** Most are **rule-decided**: `scripts/run_step.py verdicts` computes the status in code and
you write it exactly as given (SKILL.md, Verdicts). For them this file holds only what you add around the status
(`evidence_found`, `notes`, `Action:` lines). The rest are **model-decided**: no rule exists, and the entries
after the rule-decided section give the status and the reasoning.

## General principles (apply to every check)

- **Judge only what the bundle shows.** An aspect that needs a live check (backups, restore tests, who
  holds an OS identity, a functional export test, run history, an external proxy) goes in `notes` as an
  `Action:`; it never moves the status away from what the bundle's own settings support. Absence of
  run history is the normal state of a bundle, not a gap.
- **Conditional check, precondition unmet: Not Applicable**, not Fail or Needs Review. A missing key is
  a Fail only when the feature is demonstrably in use.
- **An inferred value is not evidence.** Don't mark Pass or Fail from an assumed default (e.g. a
  connection pool against an internal-database limit the bundle doesn't record). Mark **Needs Review**,
  state the inference in `notes` as an inference, and ask for the real value.
- **A hinted setting is not proof of absence.** A `parameter_hint` is a pointer, not a guarantee of
  where the setting lives. Before marking a setting absent or Fail, look for it the way the reader's
  `data-dir-config` reference ("Finding a setting reliably") describes.
- **Version gate beats feature gate.** If the check's stated minimum DSS version is above the bundle's
  `product_version`, mark **Needs Review** (the capability can't exist yet, so Fail would be unfair)
  and name the introducing version in `notes`, even if the feature is also conditional. Upgrade planning is the
  actionable point. The rules do not apply this gate themselves: when a verdict looks wrong for an old DSS,
  say so in your final summary.
- **Optional feature off but the checklist asks for acceptance or enablement (GenAI, graphics export):**
  **Needs Review** (ask whether it is intentional), not Fail. Security controls follow their own rules.
  A setting or section absent from the bundle is **Needs Review**, never treated as off.
- **Live-only aspects are an `Action:`, never a status change:** e.g. SEC-001 (id matches the customer's inventory), SEC-002 (OS
  identities exist), SEC-005 (live OS hierarchy), SCALE-011 (a project uses the connection), GENAI-004 (outbound gateway access).
- **A verdict whose reason says "ask whether intentional"** is a Needs Review: put one `Action:` bullet naming the team
  to ask (see "Format of `notes`" in SKILL.md).

## Rule-decided checks: what to write

The status comes from the verdict. Quote its `deciding_values` and add only the following.

**Security**
- **SEC-004:** give the percentage and tier, e.g. `190G = 75.7% of 251 GiB; tier target 75%`. Host RAM is `MemTotal` in GiB and
  the cgroup "G" is GiB: never mix GB and GiB. Empty per-workload placements are an observation, not a downgrade.
- **SEC-006:** DSS's own config shows only whether DSS itself terminates TLS. On Needs Review, one bullet says the bundle can't
  confirm or rule out a TLS-terminating proxy, plus an `Action:` to verify with the infrastructure team. Quote the raw server
  block in `evidence_found`. A proxy documented elsewhere in the bundle is not read by the rule: it stays Needs Review.
- **SEC-009:** give the count of authorized groups, never the names.
- **SEC-010:** give the protocol, never any secret. On Fail, `Action:` discuss the benefits of SSO with the customer.
- **ADVSEC-006:** when no custom redirect is set, say the default logged-out page is in use.
- **ADVSEC-008:** other export or clipboard keys that are set are `notes` only.
- **ADVSEC-009:** say a proxy may set the headers (the bundle can't show that). The four non-core headers are `notes` only.

**Platform, sizing and logs**
- **ARCH-001:** the status is always Needs Review. Use the reader's `node-types` and `data-dir-config` (deployer) references to find
  indicators and report what you find. On a **design** bundle, in this order:
  1. **Local Project Deployer on the design host:** one holding projects to deploy to an automation node indicates one is in use.
     Take the counts from the `local_deployer` fact, then enumerate what it holds (infrastructures, deployments, published projects, any automation-node URLs). **Put this indication,
     with counts, in the headline of `notes`** and list the URLs and enumeration in `evidence_found`. Distinguish a populated deployer
     (strong indication) from one present but empty (enabled, no sign of use). A local API Deployer targets API nodes: mention it
     separately as an API-node indication, not as evidence of an automation node.
     If the deployer fact sets `remote_host_with_local_mode`, or shows a remote host recorded under local mode, or trust-all-certificates enabled, add an `Action:` to
     confirm whether the remote setting is a leftover and whether certificate checking should be on; it does not change the status.
  2. **Remote deployer:** a design node pushing to an external Deployer URL suggests Design -> Deployer -> Automation, but any
     automation infrastructure is defined on that node, not in this bundle. Exported project bundles are weak supporting evidence.
  3. **Otherwise:** say in `notes` that no definitive configuration shows whether an automation node is deployed, and that it needs
     verification with the customer.
  On an **automation** bundle the node itself proves an automation node exists: say so, and add an `Action:` to confirm the design
  node and that projects are built there and promoted by bundle, not edited on the automation node.
- **ARCH-004:** name the data directory and the disk(s) in `evidence_found`. When the row is `undecided` (older facts without
  sanity-check codes), read the sanity-check text: a message about a rotational, HDD or SSD disk is Fail; otherwise judge from the disks.
- **SCALE-001:** loopback PostgreSQL is a pass with a `notes` bullet that it is installed locally on the DSS host (a backup and
  availability caveat). Pool size against `max_connections` and backups are `notes` only. When `facts.py`'s `internal_database`
  reports `password_stored_in_plaintext: true`, `notes` carries `Action: rotate the stored database credential and move it to a
  secrets store` (never the value); it does not change the status. False or ABSENT: add nothing.
  On the rule's Needs Review for a missing `internalDatabase.connection` override, `notes` says the embedded H2 is inferred from that
  absence, and the `Action:` is to confirm the runtime database live with the platform team (it may be a local PostgreSQL set up at
  install time and configured outside the bundle).
- **SCALE-002:** name the flavor and the estate signal in `evidence_found`; whether managed datasets actually sync is a live check.
- **SCALE-004:** say a scenario's script was not read; run history, whether cleanup runs, and whether it covers logs, idle kernels
  or both are `notes` only. If the `run_as_user_missing` fact has a count, say that the scenarios listed in it cannot run because
  their configured user no longer exists, and name any that is the only active scheduled cleanup scenario; the status is unchanged.
- **SCALE-006:** give the message counts; the warnings it lists are judged by the checks they relate to, not here.
- **SCALE-007:** make the finding useful. The bundle usually holds only a few hours of backend log, so quote counts with their
  window (e.g. `214 in ~2.6h`) in both `evidence_found` and `notes`, and group by message pattern (digits and ids normalised), not
  by raw line. When one pattern dominates (e.g. repeated rejected WebSocket sessions that were not logged in), say so in `notes`
  with its share, and put the `Action:` on the real failures (e.g. failing API calls). The reader's `data-dir-runtime-and-codeenvs`
  reference says how to count and get the window. Take the pattern groups, their shares and windows from the `backend_log` fact's
  `top_error_patterns` rather than re-counting by hand, and mention `run_as_user_missing` when its count is not zero.
- **SCALE-008:** state in `evidence_found` which of the five checks you used (RAM tier, 3x config folder, dead zone, the
  `OutOfMemoryError` count with its window); never assume a tier from RAM alone. `jek.xmx` and `fek.xmx` oversizing has no
  threshold: `notes` only. A Pass covers current sizing and the recent logs only: say in `notes` that historical JVM or native-memory
  crash dumps are not a basis for this status and that Pass is not crash-free assurance. If the `crash_dumps` fact has a count, list each dump's date, process and problem class in `notes` and add an `Action:` to review them; the status is unchanged.
- **SCALE-009:** on Needs Review, ask whether the sizing is justified. A limit that sits in a different place than its name suggests
  still counts.
- **SCALE-010:** name the non-blank values; call a non-blank engine preference the riskier one.
- **SCALE-012 to 015:** name the connections that are not set up and the missing setting (never hosts or credentials). The cloud
  storage authentication being compatible with Automatic fast-write, and Details readable by on the storage connection linked to a
  warehouse, can't be read from a bundle: an `Action:`. For Redshift, note that the Fast Path applies only to some cases.

**Always Needs Review** (the rule fixes the status; put observations in `evidence_found` and `notes`, and an `Action:` to confirm)
- **SEC-003:** the UIF security configuration is not part of a bundle, so the status is fixed. Report the cgroup hierarchies DSS controls
  that the bundle does show (the cgroup targets and their count) and whether UIF is enabled, without naming files. `Action:` check on the
  host that each of those hierarchies is listed among the additional allowed directories of the UIF security configuration.
- **SEC-008:** give the number of groups and whether any grant broad admin rights, never user or group names beyond built-in ones.
  Take the counts from the `groups` fact (see the reader's `data-dir-config` reference), not by opening the user directory.
  Whether the design suits the customer is an `Action:`.
- **SEC-011:** quote any proxy setting that is present (host only, never credentials); otherwise say none was found, and that a proxy
  may sit outside DSS. `Action:` ask for the proxy documentation.
- **SCALE-005:** mention any backup-related setting or scenario that the bundle shows; `Action:` request the backup policy (DCS: Fleet
  Manager snapshots).
- **SCALE-016:** note what supports resilience in the bundle (external database, backups seen, a remote or HA topology); `Action:`
  hold a DR/HA discussion against the customer's RPO and RTO.
- **GENAI-010, GENAI-011:** the rule gives Not Applicable when Agent Hub is not installed; keep that status.
- **GENAI-011:** say whether Agent Hub is installed and which groups exist, never user names. The group running the Agent Hub web app and
  its impersonation allowed groups are not in a bundle: `Action:` check Administration > Security > Groups, that the allowed
  groups are limited to the users who should reach Agent Hub, with no broad group such as all users.
- **GENAI-010:** say whether Agent Hub is installed and which kind of account the bundle shows managing it; `Action:` confirm it is a
  dedicated service account, not an administrator's own.

**Kubernetes and Spark**
- **ARCH-007:** note the namespace field and value seen in `evidence_found` (a templated variable such as `${namespace}` needs
  no tracing). A template alone does not prove per-user isolation: say in `notes` that variable resolution, creation policy and
  the service account's permissions are checked separately.
- **ARCH-016:** the rule passes on a default cluster alone. When the default execution config is absent, say in `notes` that readiness
  for broad offloading is not established.
- **ARCH-009, ARCH-012:** Not Applicable without a cluster attached; with one, Needs Review. ARCH-009: state the cluster kind and its API endpoint host if the reader
  publishes it; reachability in both directions (DSS to the API server, pods back to DSS) is an `Action:` live test. ARCH-012: name the configured execution configs and what is enabled (containerized recipes, notebooks, webapps, API services); `Action:` run a test in each.
- **ARCH-008, ARCH-014, ARCH-015:** with a cluster attached the status is Needs Review: add an `Action:` to run a Spark recipe and
  a notebook (ARCH-008), to review node groups and autoscaling (ARCH-014), or to compare cluster capacity with the workloads
  (ARCH-015). ARCH-008 is worded for Spark on Kubernetes: no cluster means Not Applicable even when Spark runs on YARN or Hadoop.
- **ARCH-006, ARCH-011:** the baseline sizes in the checklist are illustrative, not names or sizes to match. Identical sizing under
  different names is a real gap: say so in `notes`.

**GenAI**
- **GENAI-001:** say which envs you saw. The status covers the default envs only, not installation, build health or document extraction defaults; say so in `notes`.
- **GENAI-002:** Not Applicable without a cluster attached. With one the status is Needs Review: report what the bundle shows (whether
  the internal Hugging Face local code environment is installed, any GPU or accelerator hints in the cluster and execution configs;
  the model must not infer GPU nodes or compute capability) and add an `Action:` to confirm the GPU node group, NVIDIA compute
  capability and the code environment on the cluster.
- **GENAI-006:** name the model id when it can't be determined.
- **GENAI-007:** name the unset default ids.
- **GENAI-008:** the status is always Needs Review. Say the DSS version, and add an `Action:` to confirm the option to include AI
  assistant logs was selected when the diagnostic was generated.
- **GENAI-009:** the bundle can't verify who may deploy; never infer it from the project owner or group grants. `Action:` check the
  deployer's permissions in the security groups.

## Model-decided checks

- **Supported operating system (ARCH-003):** take the OS name and version from the bundle (the reader's
  `root-files` reference says where) and compare them with Dataiku's supported-OS documentation for the
  bundle's DSS **major** version, using the same web lookup as ARCH-002 (official Dataiku docs only, never prior
  knowledge). Listed: **Pass** (mention a deprecation notice in `notes` if the page has one). Not listed:
  **Fail**. Lookup failed or unavailable, or the OS isn't captured: **Needs Review**. Name the OS, the DSS
  major and the page consulted in `evidence_found`.

- **DSS version currency (ARCH-002):** look up the current GA release at run time, then compare the
  bundle's DSS `product_version` (the reader's `data-dir-identity` reference says where it is) against the
  latest GA's **major** version only:
  - Same major (e.g. bundle 14.x, latest GA 14.x, any minor/patch): **Pass**.
  - Bundle's major is behind: **Needs Review** (not Fail); a major gap warrants a human look at upgrade
    planning.
  - Lookup failed, returned nothing usable, or no web search tool is available: **Needs Review**. Never
    guess from prior knowledge; say in `notes` that currency could not be verified.

  State the bundle's version, the latest GA version, its release date if known, and how many majors
  behind (0 if current). Keep `notes` short (e.g. `Bundle 13.x vs latest GA 14.x (date) — 1 major
  behind`); put the full source citation in `evidence_found`.

  **Lookup procedure:** use the **extended** web-search mode every run (a standard search can miss a
  newer major). Search "Dataiku DSS latest version release notes", then once more for the next major above
  the one found (e.g. "Dataiku DSS 15 release notes"). Take the highest GA version confirmed by an
  official Dataiku source (release notes, changelog, docs.dataiku.com). If results are links only,
  `WebFetch` the official release-notes page for the newest major. Never answer from training knowledge.
