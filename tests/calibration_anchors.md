# Calibration anchors

The title each check id cited in `skills/dataiku-diagnosis-checklist-review/references/calibrations.md` had in the
bundled default checklist when its entry was written. `tests/test_calibration_ids.py` fails when the checklist no
longer matches this table or when `calibrations.md` cites an id missing here; update the entry and the row together.

| Id | Title when written |
|---|---|
| ADVSEC-006 | Redirecting to a custom URL after logout |
| ADVSEC-008 | Restricting exports |
| ADVSEC-009 | Setting security-related HTTP headers |
| ARCH-001 | Separation of Design and Automation Nodes |
| ARCH-002 | Regular DSS Version Upgrades |
| ARCH-003 | Supported Operating System Version |
| ARCH-004 | SSD Storage for DSS |
| ARCH-006 | Baseline Spark Configuration Set (High/Standard/Large-memory/High I/O) |
| ARCH-007 | Kubernetes Namespace and Auth Recommendations for Spark |
| ARCH-008 | Functional Validation of Spark Execution (Recipe & Notebook) |
| ARCH-009 | Bidirectional Network Connectivity Between DSS and Elastic AI Cluster |
| ARCH-011 | Baseline Container Execution Configs (Standard, Webapp) and Namespace Settings |
| ARCH-012 | Functional Validation of Containerized Execution Across Recipe, Notebook, Webapp, and API |
| ARCH-014 | Recommended Cluster Topology (Single Managed Cluster, Node Groups, Autoscaling) |
| ARCH-015 | Appropriate Cluster Sizing |
| ARCH-016 | Global Default Cluster and Default Execution Config Set (if Elastic AI used) |
| GENAI-001 | Internal Code Environments for RAG, Document Extraction, PII Detection |
| GENAI-002 | Hugging Face Local LLM Enablement (Conditional) |
| GENAI-004 | AI Services Terms of Use Acceptance & Enablement |
| GENAI-006 | Bring Your Own LLM - Recommended Model Versions |
| GENAI-007 | Cobuild Default LLM Configuration |
| GENAI-008 | Include AI Assistant Debug Data in Instance Diagnostics |
| GENAI-009 | Agent Hub Deployment Required Permissions |
| GENAI-010 | Use Service Account for Agent Hub Management |
| GENAI-011 | Agent Hub WebApp Impersonation - Allowed Groups Scope |
| SCALE-001 | External PostgreSQL Runtime Database |
| SCALE-002 | Appropriate Metastore Configured |
| SCALE-004 | Admin Project for Garbage Collection |
| SCALE-005 | Environment Backup Policy |
| SCALE-006 | Usage of Instance Sanity Check |
| SCALE-007 | Backend.log Error Review |
| SCALE-008 | Backend Xmx Sizing |
| SCALE-009 | Flow Limits Sizing (Max Jobs, Max Activities) |
| SCALE-010 | Preferred Connections and Engines Settings |
| SCALE-011 | Remove filesystem_root Connection |
| SCALE-012 | Cloud Object Storage Configuration (Details Readable By, HDFS Interface) |
| SCALE-013 | Snowflake Connection Configuration |
| SCALE-014 | Databricks Connection Configuration |
| SCALE-015 | Amazon Redshift, Google BigQuery, Azure Synapse Connection Configuration |
| SCALE-016 | Disaster Recovery Strategy Discussion |
| SEC-001 | Verify/Capture Instance IDs |
| SEC-002 | User Isolation Framework (UIF) Enabled with Appropriate Impersonation Rules |
| SEC-003 | UIF-Managed CGroup Hierarchies Allowed Directories |
| SEC-004 | CGroups Enabled with Memory Limit per Sizing Heuristic |
| SEC-005 | JEK-Specific CGroup Limits Left Unconfigured |
| SEC-006 | HTTPS Access Configured for DSS |
| SEC-008 | DSS Groups Security Model Appropriately Defined |
| SEC-009 | LDAP Authorized Groups Configured |
| SEC-010 | SSO Enablement Reviewed |
| SEC-011 | Proxy Configuration Reviewed and Documented |
