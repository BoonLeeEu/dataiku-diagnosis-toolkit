# `<mirror>/config/` — the instance + project metastore

The richest area of the bundle. All paths below are relative to the data-dir mirror root (see
`references/data-dir-identity.md` for how to find it).

## Instance-wide config (top-level files under `config/`)

| File | Contains | Notes |
|---|---|---|
| `general-settings.json` | Master instance settings: LDAP/SSO/Azure AD auth, proxy, mail, container/k8s settings, Spark/Hadoop/Hive settings, security, code-env defaults, GenAI settings, job concurrency (`maxRunningActivities`), CORS, git integration | Largest/most important config file (tens of KB). Also holds `deployerClientSettings` (mode `REMOTE` = this node is a deployment target) and `governIntegrationSettings` (Govern MLOps integration) — see `references/node-types.md`. For cgroups/container/Spark/K8s resource settings, see the resource-governance subsection below; for the internal (H2 vs. PostgreSQL) database, see the subsection right after it |
| `license.json` | License/entitlement info: licensee, instanceId, licenseKind, feature flags (`maxFullDesigners`, `maxAIConsumers`, ...) | May be a signed/opaque blob (`{content, r1Sig, r1Pub, r1PubSig}`) rather than flat JSON |
| `connections.json` | Every configured data connection (DB/cloud/filesystem/HDFS/MFT) | **Top-level shape is `{"connections": {<name>: {...}}}`**, not a bare name-keyed dict. Fields per connection: `type`, `params`, `allowedGroups`, `credentialsMode`, `allowWrite`, `allowManagedDatasets`. `params` can hold plaintext secrets: inspect with `scripts/peek.py`, never dump |
| `users.json` | Full user + group directory | Per user: `login`, `displayName`, hashed `password`, `userProfile`, `groups`, `sourceType` (LDAP/local), `enabled` — contains PII, handle carefully |
| `dip.properties` | Low-level backend property overrides | `key=value` lines, e.g. `dku.exports.disableAllExports=true` |
| `personal-apikeys.json` / `public-apikeys.json` | API key metadata (scopes, owning user) | |
| `variables.json` | Instance-level global variables | |
| `messaging-channels.json` | Notification channel configs (email/Slack/Teams/webhook) | |
| `achievements.json` | Gamification/onboarding tracker | Low troubleshooting value |
| `project_folders/<id>.json` | UI project-folder grouping tree | |
| `workspaces/<name>.json` | Cross-project "workspace" (collaboration space) definitions | |
| `clusters/<name>.json` | Manually-defined compute cluster (Hadoop/Spark/k8s) that can override instance-wide defaults | See the resource-governance subsection below |
| `data-collections/*.json`, `data-quality-templates/`, `global-flow-filters.json` | Secondary/supporting config areas | Low priority unless specifically asked about |
| `.mainlock`, `.wlock`, `.ts`, `.dku-projects-gitignore` | DSS's internal git/locking bookkeeping for the config dir itself (DSS versions its own config via an internal git repo) | Not user-facing data |

## Resource governance: cgroups, containers, Spark, Kubernetes

`general-settings.json` holds several **separate blocks that must be read together** to answer a
resource/OS/deployment question — none of them alone tells the full story of how DSS restricts or
requests compute:

| Block | Controls | Key fields |
|---|---|---|
| `cgroupSettings` | OS-level confinement of DSS-launched processes on *this host* | `enabled`, `cgroupsVersion` (`CGROUPS_V1`/`CGROUPS_V2`), `hierarchiesMountPoint`, then one entry per workload type (`mlKernels`, `pythonRRecipes`, `pythonScenarios`, `jupyterKernels`, `mlRecipes`, `edaRecipes`, `webappDevBackends`, ...), each with `targets[].cgroupPathTemplate` (e.g. `memory/DSS/${user}/mlKernels`). This is the configured *template* — the root file `cgroups_usage.txt` shows the resolved paths and live usage; read both together. `scripts/facts.py` reports `cgroups.target_counts` (targets per workload category; a category missing from it is not configured, a count of 0 is configured with no target; job execution kernels are `jobExecutionKernels`) |
| `containerSettings` | Non-Spark containerized execution (Python/R recipes, webapps, plugin components) in Docker or Kubernetes | `executionConfigs[]` — named profiles (e.g. `py_small_config`) with `type` (`KUBERNETES`/`DOCKER`), `kubernetesResources` (`memRequestMB`, `memLimitMB`, `cpuRequest`, `cpuLimit`), `kubernetesNamespace`, `repositoryURL`/`imagePullSecretName`; `executionConfigsGenericOverrides` is the fallback profile when nothing more specific applies |
| `sparkSettings` | Spark job resource requests | `sparkEnabled`, `executionConfigs[]` — named profiles (e.g. `spark_small_config`) with `conf[]` key/value pairs and a `kubernetesSettings` block. The actual resource ask is `spark.executor.instances`/`spark.executor.memory`/`spark.executor.cores`/`spark.driver.memory`; on Spark-on-Kubernetes, `spark.kubernetes.*` keys (`spark.kubernetes.memoryOverheadFactor`, `spark.kubernetes.executor.limit.cores`, `spark.kubernetes.container.image.pullSecrets`) show how that ask is packaged for the k8s scheduler. Each config's `kubernetesSettings.managedKubernetes` (bool) says whether that profile targets an attached managed k8s cluster; when it does, `kubernetesSettings.managedNamespace` is the namespace Spark pods land in — see the namespace-per-user note below |
| `useImplicitK8sCluster` (top-level bool) | Whether DSS auto-manages an implicit k8s execution context, vs. requiring explicit named execution configs / a manual cluster | Observed `true` with empty `containerSettings.executionConfigs`/`sparkSettings.executionConfigs` in two samples, and `false` with 5 populated K8s execution configs plus a manual `clusters/<name>.json` in a third — small sample, but the two modes tracked together in every sample seen |
| `k8sPoliciesSettings` | Admin-defined constraints on what execution configs/users may request | `policies[]` — empty in every sample seen, so its populated shape is unverified |
| `hadoopSettings` | Instance-wide Hadoop/Kerberos defaults (YARN-based Spark, distinct from container-based Spark) | `kerberosLoginEnabled`, `dssPrincipal`, `dssKeytabPath` |
| `computeResourceUsageReportingSettings` | Whether DSS periodically reports its own k8s usage back | `periodicKubernetesUsageReporting`, `includeBuiltinCluster`, `namespacePattern` |
| `limits` | Soft/hard byte ceilings on specific in-memory operations | e.g. `memSampleBytes.soft/hard`, `shakerMemTableBytes.hard` — a narrower, unrelated notion of "limit" from cgroups |

**`config/clusters/<name>.json`** (one file per manually-defined compute cluster) can **override**
the instance-wide Hadoop/Hive/Impala/Spark/container defaults above for jobs that target it. Each
has `architecture` (e.g. `KUBERNETES`), `owner`, `permissions` (which groups may use it), and
`override*Settings` blocks (`overrideHadoopSettings`, `overrideSparkSettings`,
`overrideContainerSettings`, ...) whose boolean sub-fields say *which* instance defaults this
cluster replaces — a `false` sub-field means that setting still falls through to
`general-settings.json`. Read a cluster file's overrides alongside the instance defaults, not
instead of them.

**How a project actually selects a profile**: a recipe's own JSON names one of these profiles.
Confirmed in a Spark-engine recipe (`.join`, one sample): `params.engineParams.spark.sparkConfig.inheritConf`
holds a `sparkSettings.executionConfigs[].name`, and `params.engineParams.containerSelection.containerMode`
is `INHERIT` (use the project/instance default) or an explicit mode naming a
`containerSettings.executionConfigs[].name`. So the full chain to answer "how will this
recipe/job request resources from Kubernetes" is: the recipe/scenario JSON (which profile is
selected) → that named profile in `general-settings.json` (or a `clusters/<name>.json` override,
if a manual cluster is targeted) → cgroup/K8s enforcement, cross-checked at runtime via
`cgroups_usage.txt` and `docker_images_listing.txt` (root files — see
`references/root-files.md`). The recipe-level field names above are confirmed only for a
Spark/join recipe; other recipe, scenario, or notebook types may expose the same selection under
different field names — verify before asserting for those.

**Where the container defaults live.** `defaultExecutionConfig`, `defaultExecutionConfigForVisualRecipesWorkloads` and `cdeEnabled` (containerized visual recipes) are keys of `containerSettings`, not top-level (an empty string means unset; `cdeEnabled` is true in all three samples). `facts.py` `kubernetes` reports them with the cluster attachment and each container and Spark execution config's sizing, reduced to names and numbers (a namespace reads `templated`, `fixed` or `ABSENT`, never the name). A Spark config's resources come from its `conf` entries, and `kubernetesSettings.managedKubernetes` false means it targets YARN or standalone Spark, not Kubernetes (both GE 2026-08 samples).

**Is a Kubernetes cluster attached?** Check both places, not one: a cluster is attached when
`config/clusters/` holds a `<name>.json` **or** `general-settings.json` has a non-empty top-level
`defaultK8sClusterId`. No attached cluster = `config/clusters/` empty/absent **and** no
`defaultK8sClusterId` (and no cluster reference in the execution configs). In the samples, the
two bundles with `useImplicitK8sCluster: true` had neither; the one with `useImplicitK8sCluster:
false` had `defaultK8sClusterId` set to the name of its `clusters/<name>.json`. Each cluster file
carries `type` (`manual` in the sample — a cluster registered externally, as opposed to one DSS
provisioned) and `architecture` (`KUBERNETES`); read `type` before assuming DSS manages the
cluster's namespaces or lifecycle. Only one `manual` cluster file was seen, so the value used for
a DSS-provisioned cluster is unverified. Note the two flags are independent: that same sample had
a `manual` cluster file **and** `kubernetesSettings.managedKubernetes: true` on all three Spark
profiles, so don't infer one from the other.

**Where the Spark-on-Kubernetes namespace lives**: each `sparkSettings.executionConfigs[]` entry
has `kubernetesSettings.managedKubernetes` (bool) — whether that profile targets an attached
managed k8s cluster (EKS/GKE/AKS) vs. a self-managed/on-prem one — and
`kubernetesSettings.managedNamespace`, the namespace Spark pods for that profile land in. The
analogous field for non-Spark k8s execution is
`containerSettings.executionConfigs[].kubernetesNamespace`. Both fields can hold either a static
literal or a `${...}`-style dynamic variable (e.g. `${namespace}`), resolved by DSS per job/user at
runtime. Confirmed across 3 samples: the one bundle with `managedKubernetes: true` used
`"${namespace}"` for `managedNamespace`; the two bundles with `managedKubernetes: false` both
hardcoded `"default"`. Whether a given value satisfies a particular per-user-isolation requirement
is a judgment call for the evaluating skill/checklist, not asserted here.

## Internal database: H2 vs. PostgreSQL

`general-settings.json` → top-level `internalDatabase` says whether DSS's internal database (used
for internal/managed-storage SQL needs, distinct from the metastore-as-config-files described in
this document) is the bundled embedded H2 or an external server:

- **`internalDatabase.connection` present**, with `connection.type` (e.g. `"PostgreSQL"`) and
  `connection.params` (`host`, `port`, `db`, `user`, and a **plaintext `password`** — sensitive,
  handle carefully) → DSS is using that external database server.
- **`internalDatabase.connection` absent** (only pool-tuning fields like
  `externalConnectionsMaxIdleTimeMS`/`maxPooledExternalConnections` remain) → DSS is using its
  **default embedded H2** database. This is an inference from absence, not a literal
  `"type": "H2"` string — no sample observed that literal value anywhere in `config/`.

**Don't confuse this with** the `databases/<name>.mv.db` files under the data-dir mirror root
(`jobs.mv.db`, `flow_state.mv.db`, `discussions.mv.db`, `trust_db.mv.db`,
`user_offline_queues.mv.db`, `dss_usage.mv.db`, `hive-catalog.mv.db`, `labelings.mv.db`,
`persistent_notifications.mv.db`, `user_interests.mv.db`, `experiments.mv.db`, ...). Those are
H2-format files for a fixed set of small internal subsystems, and they exist **regardless** of the
`internalDatabase` setting — observed present and identical in name across all 3 samples (2 with
`internalDatabase` set to external PostgreSQL, 1 with no override). They are not what
`internalDatabase` controls. `_pre_migration_backup_<timestamp>/databases/` siblings are prior
versions kept across DSS upgrades — the timestamp marks the upgrade date, not current state.

## Plugins

`config/plugins/<plugin-id>/settings.json` — one entry per **installed** plugin (enabled
components, permissions, presets, `codeEnvName`). The folder names under `config/plugins/` *are*
the list of installed plugin IDs. This is present and populated on both design and automation
nodes — installation/enablement state travels with the instance regardless of where the plugin
was authored.

Actual plugin **source code**, when present, lives separately at `<mirror>/plugins/dev/<plugin>/`
— see `references/data-dir-runtime-and-codeenvs.md`.

## Deployer config (design/deployer-host only)

`config/api-deployer/{infras,published-services,deployments}/*.json` and
`config/project-deployer/projects/` hold deployer infrastructure/deployment target definitions.
These directories are typically **absent** on a pure automation node (which is a deployment
*target*, not a deployer *host* — see `general-settings.json`'s `deployerClientSettings.mode`).

Observed shape on the one design sample that hosted a local deployer: `api-deployer/` held
`infras/<name>.json`, `published-services/<id>.json` and `deployments/<service>-on-<infra>.json`
(populated), while `project-deployer/` held only `projects/<KEY>.json` (one published project) —
no `infras/` or `deployments/` under it. Whether a populated Project Deployer also has `infras/`
and `deployments/` is unverified. `api-deployer/` targets API nodes, not automation nodes. The
mirror may not copy these subtrees, so also check `config_listing.txt`/`datadir_listing.txt`.
`facts.py` `deployer` sets `remote_host_with_local_mode` when `mode` is `LOCAL` yet a `nodeUrl` host is recorded (probably a leftover remote setting; unverified), and reports `trust_all_ssl_certificates` as stored. `deployerClientSettings.mode` was `LOCAL` on that sample; `REMOTE` carries a `nodeUrl` to an
external Deployer. Exported project bundles live under `<mirror>/bundles/<PROJECT>/` and are
usually visible only in `datadir_listing.txt`.

## Finding a setting reliably

- A checklist's or doc's hinted path is a pointer, not a guarantee. Before concluding a key is
  absent, search the whole file for the **leaf key**. Example: `traceExplorerDefaultWebApp` sits
  under `generativeAISettings.llmTraceSettings`, not at the top level.
- Limits can sit under a block other than their name suggests. Example: `jekSettings.maxRunningJobs`
  (a job-execution limit) vs. the top-level `maxRunningActivities`; the former was `0` in two
  samples, which is "unset", not "zero allowed".
- Advanced security and behaviour keys (header settings, `dku.feature.*`, upload extensions) can
  live in `dip.properties` (`key=value`) or `install.ini` instead of `general-settings.json`.
  Search all three before calling a setting absent.
- **Session and link settings are in `general-settings.json` → `security`**, not only in the UI:
  `sessionsMaxTotalTimeMinutes` and `sessionsMaxIdleTimeMinutes` (`0` = no limit), `forceSingleSessionPerUser`,
  `ipBoundSessions`, and `disableDataTableLinks` (the equivalent of the `dku.feature.dataTableLinks.enabled`
  property). Present in both a design and an automation sample; check there before calling one UI-only.
- **User isolation (UIF / impersonation)** is `general-settings.json` → top-level `impersonation`: `enabled`, `useHadoopDelegationTokens`, `userRules[]`, `groupRules[]`. Rules carry `scope` and `type` (`IDENTITY`, or `SINGLE_MAPPING` with `dssUser`/`targetUnix`/`targetHadoop` and sometimes `ruleFrom`). Present, enabled, in all three samples (two design, one automation). `security.webappsIsolationMode` is the separate webapp-isolation setting. The `install.ini` `[mus]` wrapper is only the OS side, so check this block before saying UIF is off.
- **Metastore and graphics export** are top-level in `general-settings.json`: `metastoreCatalogsSettings.synchronizeTo.flavor` (`HIVESERVER2` in all three samples; other flavors unobserved) and the boolean `graphicsExportsEnabled` (`true` in two samples, `false` in one). Neither is in `dip.properties`. `facts.py` `metastore_and_exports` reports both, plus the estate signals that decide whether a flavor fits: `hiveSettings.enabled` and `DKU_HADOOP_ENABLED` in `diag.txt`'s environment (`ABSENT` when not recorded).
- **Webapp API-ticket groups**: `config/users.json` → `groups[]` entries carry
  `canObtainAPITicketFromCookiesForGroupsRegex` (a regex, empty when not granted), the "allowed groups" for
  webapp impersonation.
- **Is an optional feature in use?** GenAI/Hugging Face signals seen: `localAIServerSettings.*UseLocal`
  (booleans such as `prepareAICompletionUseLocal`, `aiGenerateSQLUseLocal`), and
  `generativeAISettings`. **Bring Your Own LLM** is active when `localAIServerSettings.mainLLMId` or
  `referenceProjectKey` is set (field names from Dataiku's checklist; not yet seen populated in a sample bundle, so
  verify when one appears); a `CustomLLM` connection alone does not make it active (`facts.py` `byo_llm`). **Agent Hub**: an `agent-hub` directory under `config/plugins/`, an `AGENT_HUB`
  project under `config/projects/` with a `web_apps/` entry (and `agent-tools/`), seen in one design sample.
  Still unverified: `aiDrivenAnalyticsSettings.agentBuildingSettings` (Cobuild default LLM ids) and an `INTERNAL_huggingface` code env.
  **GenAI defaults** (`facts.py` `genai_settings`): `generativeAISettings.defaultRetrievableKnowledgeCodeEnv` and
  `presidioBasedPIIDetectionCodeEnv` name the default code envs for RAG and PII detection (an unset key means none is set in
  the file; an `INTERNAL_` prefix marks an internal env). `aiDrivenAnalyticsSettings.dataikuAIServicesTermsOfUseAccepted` is the
  AI Services terms flag; the enable flags are `enabled` (older DSS) or per feature (`prepareAICompletionEnabled`,
  `aiGenerateSQLEnabled`, `aiExplanationsEnabled`, `storiesAIEnabled`). Checked on the three sample bundles.

## Connections (`connections.json`) of interest

Besides `type`/`params`/`allowedGroups`: `detailsReadability` (`{readableBy, allowedGroups}`)
says who may read the connection's details (credentials); `params.root` is the filesystem root
for filesystem/HDFS connections; `params.hdfsInterface` appears on the cloud object storage connections (GCS and Azure in the samples, value `NONE` when off). BigQuery and SQL Server carry a boolean `params.useAutoFastPath`; SQL Server with `params.azureDWH` is Synapse. No S3, Snowflake, Databricks, Redshift or Synapse connection exists in the three samples, so their fast-write setting names are unverified: `facts.py` finds fast-write, Spark native integration and UDF settings by name pattern and treats a non-blank value as set (`connections.warehouses`). DSS also
flags gaps itself in `run/sanity-check.json` (e.g. `WARN_CONNECTION_SPARK_NO_GROUP_WITH_DETAILS_READ_ACCESS`),
see `references/data-dir-runtime-and-codeenvs.md`. Connection `params` can hold secrets: never
dump a whole connection.

## `config/projects/<PROJECT_KEY>/` — one project's full definition

Present on both design nodes (live-authored) and automation nodes (bundle-activated — the content
shape is the same either way). Each project directory is its own internal git repo
(`.git/logs/HEAD` shows metadata edit-history timestamps).

| Subpath | Contains |
|---|---|
| `params.json` | Project settings, dashboard authorizations, permissions |
| `tags.json`, `badges.json` | Tags / gamification badges |
| `apikeys.json`, `variables.json` | Project-scoped API keys and variables |
| `active-bundle.json` | Mainly seen on automation nodes: `{"bundleId": "...", "activatedOn": "..."}` — which deployed bundle is currently live for this project. Rare but possible on a design node too (e.g. a project used to test-activate a bundle before deployment) — its presence signals bundle activation happened, not the node type itself |
| `datasets/<name>.json` | Dataset definitions: type, schema, connection, format params |
| `recipes/<name>.<type>` (+ `.json`) | Recipe definitions — `.shaker` (visual prep steps), `.py` (Python recipe code), `.sync`/`.hive`/`.impala`, `.prediction_training`/`.prediction_scoring`/`.doctor_prediction_training` (ML recipes) |
| `analysis/<id>/{core_params.json, ml/<id>/params.json}` | Visual ML "Lab" analysis configs (algorithms, features, splits) |
| `saved_models/<id>.json` | Deployed/saved ML model metadata |
| `model_evaluation_stores/`, `model_comparisons/` | Model evaluation & comparison configs |
| `scenarios/<name>.json` (+ paired `.py` for custom-Python steps) | Automation scenario **definitions** (steps, triggers, reporters) — NOT run history, see `references/limitations.md` |
| `dashboards/<id>.json` | Dashboard layout + tile definitions |
| `insights/<id>.json` | Individual insight (chart/dataset-viewer/report) definitions |
| `wiki/articles/`, `wiki/taxonomy.json` | Project wiki content |
| `ipython_notebooks/*.ipynb` (or `notebooks/`) | Actual Jupyter notebook content, including code cells |
| `lib/{python,R}/`, `external-libraries.json` | Project-local shared library code usable across recipes/notebooks |
| `lambda_services/<id>.json` | API/Lambda service endpoint definitions — includes activated API-scoring projects on automation nodes |
| `managed_folders/`, `zones/`, `statistics_worksheets/`, `explore/` | Supporting flow/UI artifacts |
| `pictures/` | Thumbnails for dashboards/insights/project |

**Scenario storage forms.** `type: step_based` keeps its work in `params.steps[]` (`type: runnable`). `type: custom_python` has only `params.envSelection` and a sibling `<name>.py` holding the logic. In the automation sample's `ADMINPROJECT`, 1 of 14 scenarios is step-based and 13 are `custom_python`, so an empty `params.steps` does not mean an empty scenario.

This confirms recipes, ML analyses, scenarios, notebooks, dashboards, wikis, and project-local
library code are all captured as real content — the complete design-time (or activated-bundle)
authoring surface of the project.
