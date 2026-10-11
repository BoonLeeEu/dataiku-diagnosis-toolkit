# Verdict rules (the spec of the code-decided checks)

> **Not read during a review.** `scripts/run_step.py verdicts` computes these statuses and the model writes them as
> given (`skills/dataiku-diagnosis-checklist-review/SKILL.md`, Verdicts). This file is the human-readable spec for the owner and for whoever changes a rule: a rule
> in `skills/dataiku-diagnosis-checklist-review/scripts/rules_*.py` and its row here change together. `tests/test_verdict_rules_doc.py` fails when a registered rule
> has no row, or a row has no rule. What the model adds to `notes` for these checks is in `skills/dataiku-diagnosis-checklist-review/references/calibrations.md`.
>
> Judgment only: which status a fact value earns. Where a value lives is the reader's business.

**Conventions**
- A fact or section missing from the bundle is **Needs Review**, never an assumed Fail or Not Applicable, except where a row
  says otherwise (SCALE-006, ADVSEC-007/008 with no properties file, GENAI-005/006 with no BYO block, GENAI-009 with no
  plugins).
- A Needs Review that says "ask whether intentional" means the model puts an `Action:` asking the customer or the owning team.
- Pass, Fail and Partial are never given for want of a live test (backups, restore, an external proxy, who holds an OS
  identity): that is an `Action:` in `notes`, not a status.
- Known gap: the rules do not apply the version gate (a check's minimum DSS version above the bundle's). It mostly works
  because the settings are missing on older versions, which gives Needs Review.
- Every rule is keyed by check id and guarded by the check's title (`verdicts.py`); a row whose title differs gets no verdict.

## Security (`rules_security.py`)

| Id | Pass | Fail | Other |
|---|---|---|---|
| SEC-001 instance id | id present in the bundle | none | |
| SEC-002 UIF | enabled with at least one user or group rule | disabled | Partial: enabled, no rules |
| SEC-005 JEK cgroups | no JEK-specific target (category absent or 0) | one or more targets, even with cgroups off | |
| SEC-006 HTTPS | DSS terminates TLS itself (ssl on and a certificate) | never | Needs Review otherwise: a proxy can't be ruled out |
| SEC-007 secure cookies | on | never | off = Needs Review |
| SEC-009 LDAP groups | LDAP on, one or more authorized groups | never | LDAP on, none = Needs Review. Not Applicable: LDAP off |
| SEC-010 SSO | SSO enabled (whatever LDAP is) | SSO disabled | flag missing = Needs Review |
| ADVSEC-001 error stacks | hidden | not hidden | |
| ADVSEC-002 version info | hidden before login | not hidden | |
| ADVSEC-003 sessions | either timeout above 0 | both 0 (unlimited) | |
| ADVSEC-004 single session | forced | not forced | |
| ADVSEC-005 user/group visibility | restricted | not restricted | |
| ADVSEC-006 logout redirect | valid http or https custom URL, or the default logged-out page | never | custom redirect with another scheme, or an unrecognised behaviour = Needs Review |
| ADVSEC-007 wiki uploads | an extension list is set | none set (a missing properties file counts as none) | |
| ADVSEC-008 exports | any export-disable key true | none (a missing properties file counts as none) | |
| ADVSEC-009 HTTP headers | all six core headers set restrictively | none of the ten configured | Partial: some set. The other four are notes only |
| ADVSEC-010 iframe | hosting off | on with secure cookies off | on with secure cookies on = Needs Review |
| ADVSEC-011 table links | disabled (either setting) | never | not disabled, or the setting missing = Needs Review |
| ADVSEC-012 edit profile | users can't edit | never | can edit = Needs Review |

The six core headers and their restrictive values: content-security-policy (non-empty), x-frame-options (SAMEORIGIN or
DENY), x-content-type-options (nosniff), x-xss-protection (set and not 0), hsts-max-age (above 0), referrer-policy (non-empty).

## Platform, sizing and logs (`rules_platform.py`)

| Id | Pass | Fail | Other |
|---|---|---|---|
| ARCH-001 design/automation separation | never | never | Needs Review for every node type (design, automation, other) and when the node type is missing: one bundle never shows the other node |
| ARCH-004 SSD | every data-directory disk non-rotational | a rotational disk, or a sanity-check code naming the disk type (even when disks can't be read) | Needs Review: undeterminable. Undecided (model reads the text) only with facts that carry no message codes |
| SEC-004 cgroups memory | limit within 10% of the RAM tier's target (either side) | cgroups disabled | Needs Review: limit 80% of RAM or more (checked first); more than 10% from target; enabled with no limit; settings or host memory missing |
| SCALE-001 PostgreSQL | PostgreSQL, local or remote | any other database | Needs Review when the database or host can't be read. With no external `internalDatabase.connection` override the reason says DSS then uses its embedded H2 (an inference) |
| SCALE-002 metastore | Hive on a Hadoop estate; DSS-internal with none | never | Glue, estate mismatch, unknown flavor = Needs Review |
| SCALE-012 cloud object storage | every S3, Azure or GCS connection readable by someone and (where the reader found it) an HDFS interface set | none of them set | Partial: some. Not Applicable: no such connection. Needs Review: readable-by unknown |
| SCALE-013 Snowflake | every Snowflake connection has fast-write set (and Spark native integration and UDF where found) | none set | Partial: some. Not Applicable: no Snowflake connection. Needs Review: fast-write setting not found |
| SCALE-014 Databricks | every Databricks connection has fast-write set | none set | Partial: some. Not Applicable: none. Needs Review: fast-write setting not found |
| SCALE-015 Redshift, BigQuery, Synapse | every such connection has fast-write set | none set | Partial: some. Not Applicable: none. Needs Review: fast-write setting not found. SQL Server flagged as Azure Synapse counts as Synapse |
| SCALE-003 graphics export | on | never | off = Needs Review |
| SCALE-004 cleanup project | an active scheduled step-based scenario with cleanup steps | no candidate project, or no active scenario | Needs Review: scheduled but purpose unclear (or scripted), or active but unscheduled; project list missing |
| SCALE-006 sanity check | output present with messages | missing or empty | |
| SCALE-007 backend log | no ERROR, FATAL or WARN | never | any such entry = Needs Review |
| SCALE-008 backend Xmx | all rules met and every input present | any miss: below the RAM tier (4g above 12 GiB, 8g above 30, 16g above 95), under 3x the config folder, in the 32 to 48 GB dead zone, or any OutOfMemoryError | Needs Review: nothing missed but an input absent, or no Xmx |
| SCALE-009 flow limits | all set; activities 30 to 50; per-job 5 | any limit 0 or blank | out of range = Needs Review |
| SCALE-010 preferences | all blank (DSS's own default format list counts as blank) | never | any non-blank = Needs Review |
| SCALE-011 filesystem_root | removed | still present | |

SEC-004 tiers (host RAM `R` in GiB, cap `L` in GiB): over 120 GiB target 75% of `R`; 60 to 120 target 66% of `R`; 30 to 60 target `R` minus 20 GiB; under 30 target 50% of `R`.

Cleanup steps (SCALE-004) are those whose name says clear, purge, delete, clean, remove, vacuum or prune; scheduled means an
active time-based trigger. SCALE-008 judges every available input; a confirmed miss wins over a missing input.

## Kubernetes and Spark (`rules_k8s.py`)

A cluster is attached when a cluster definition file exists or a default cluster id is set. With none attached, every
Kubernetes-only check below is **Not Applicable**, even if Kubernetes execution configs are defined.

| Id | Pass | Fail | Other |
|---|---|---|---|
| ARCH-005 Spark config | enabled with a config that sets resources | enabled, none | Not Applicable: Spark off. Needs Review: flag missing |
| ARCH-006 Spark baseline | two or more differently sized configs | none defined | Not Applicable: Spark off. Needs Review: one, or all identical |
| ARCH-007 namespaces | every Kubernetes-targeting config uses a templated per-user namespace | never | fixed or missing namespace = Needs Review. Spark configs that don't target Kubernetes are ignored |
| ARCH-008 Spark validation | never | never | Not Applicable: no cluster attached. Needs Review: cluster attached (a live run can't be shown by a bundle), or the attachment unreadable |
| GENAI-002 Hugging Face local LLM | never | never | Not Applicable: no cluster attached (local models run on an Elastic AI cluster). Needs Review: cluster attached (GPU nodes, compute capability and the code env can't be shown by a bundle), or the attachment unreadable |
| ARCH-009 DSS to cluster connectivity | never | never | Not Applicable: no cluster attached. Needs Review: cluster attached (reachability is a live test), or the attachment unreadable |
| ARCH-010 container config | a Kubernetes config with a memory limit | cluster attached, none defined | configs but no limit = Needs Review |
| ARCH-011 container baseline | two or more differently sized container configs | cluster attached, none defined | one, or all identical = Needs Review |
| ARCH-012 containerized execution | never | never | Not Applicable: no cluster attached. Needs Review: cluster attached (it needs a live run), or the attachment unreadable |
| ARCH-013 cluster | a Kubernetes cluster definition in the bundle | never | attached with no definition = Needs Review |
| ARCH-014 cluster topology | never | never | Not Applicable: no cluster attached. Needs Review: cluster attached (topology is never in a bundle) |
| ARCH-015 cluster sizing | never | never | Not Applicable: no cluster attached. Needs Review: cluster attached (capacity is never in a bundle) |
| ARCH-016 global defaults | cluster attached and a default cluster set | cluster attached, no default cluster | unreadable setting = Needs Review. The default execution config is a note only |
| ARCH-017 containerized visual recipes | feature on and a default visual-recipe config set | never | anything else = Needs Review |

## GenAI (`rules_genai.py`)

| Id | Pass | Fail | Other |
|---|---|---|---|
| GENAI-001 code envs | default envs are internal | no default env set | a non-internal env = Needs Review. GenAI settings missing = Needs Review |
| GENAI-003 Trace Explorer | default project and web app set | block present, none set | block missing = Needs Review |
| GENAI-004 AI Services | terms accepted and a feature enabled | never | otherwise Needs Review (optional feature) |
| GENAI-005 BYO reference and model | both set | active, one missing | Not Applicable: BYO inactive or block missing |
| GENAI-006 BYO model version | every LLM id ChatGPT 5.2 or later | any id older (`gpt-5` counts as 5.0) | undeterminable id = Needs Review. Not Applicable: BYO inactive |
| GENAI-007 Cobuild defaults | all three default ids set | never | any unset, or block missing = Needs Review |
| GENAI-008 AI assistant logs | never | never | always Needs Review: the option's state can't be read from a bundle (the reason says whether DSS is older than 14.7) |
| GENAI-009 Agent Hub | never | never | installed = Needs Review. Not installed, or no plugin configuration = Not Applicable |
| GENAI-010 Agent Hub service account | never | never | installed = Needs Review. Not installed, or no plugin configuration = Not Applicable |
| GENAI-011 Agent Hub impersonation scope | never | never | installed = Needs Review. Not installed, or no plugin configuration = Not Applicable |

A connection setting counts as set when it holds a value (the reader finds the warehouse fast-write, Spark native and UDF settings by name pattern). The bundle can't link a warehouse to its cloud storage connection, so storage authentication compatibility and details-readable on the linked storage are an `Action:`.

BYO mode is active when a main LLM id or a reference project key is set; a custom LLM connection alone does not make it active.

## Always Needs Review (`rules_review.py`)

Live or customer-practice checks a bundle can never settle: the status is fixed and the model reports what the bundle does show and an `Action:` to confirm the rest.

| Id | Pass | Fail | Other |
|---|---|---|---|
| SEC-003 UIF cgroup directories | never | never | always Needs Review: the UIF security configuration is not in a bundle |
| SEC-008 groups security model | never | never | always Needs Review |
| SEC-011 proxy configuration | never | never | always Needs Review |
| SCALE-005 backup policy | never | never | always Needs Review |
| SCALE-016 disaster recovery | never | never | always Needs Review |

## Stays with the model

ARCH-002 and ARCH-003: they need a live web lookup (the current GA release, the supported-OS page), so the model decides them. Their guidance is in `calibrations.md`.
