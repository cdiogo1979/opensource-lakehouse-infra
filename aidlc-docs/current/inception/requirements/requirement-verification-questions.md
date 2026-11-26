# Requirement Verification Questions — StarRocks Audit Capture

Intent `20261125-starrocks-audit-capture`. Fixed by the paired intent (not asked again): AuditLoader into `starrocks_audit_db__.starrocks_audit_tbl__` with a 7-day time-to-live; the audit product's bronze task reads it with `SELECT *` from the writer (Airflow) and from owners and developers (Jupyter); `lakehouse_starrocks.connect()` is the connection; the audit product's analysts get no access to it. Answer each question with a letter after `[Answer]:`; choose the last option (Other) and describe if none fits.

## Question 1
Which StarRocks identity should the AuditLoader plugin use to load the staging table (its `plugin.conf` holds a user and password)?

A) A dedicated local StarRocks user `srv-auditloader` with a generated password in `.runtime/credentials/` and only `INSERT` on the staging table; the plugin package with its `plugin.conf` is built at bootstrap under `.runtime/`, never in the repository

B) `root`, with the existing root password file

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
Where should the AuditLoader plugin package come from?

A) The official release from GitHub (`StarRocks/fe-plugins-auditloader`), pinned to a version compatible with 4.1.7 and checked against a SHA-256 recorded in the repository, downloaded at bootstrap (cached under `.runtime/`)

B) Built from source in a container at bootstrap

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
How should the `SELECT` grant on the staging table be modeled, given the bootstrap revokes undeclared grants on product roles?

A) A new optional block in the product file, for example `platform_sources: {starrocks_audit: {owner: read, developer: read, writer: read}}`; only `audit.yaml` uses it; bootstrap and the reconciler grant and keep it like other access

B) A platform setting naming the one product that may read the audit log (for example `LAKEHOUSE_AUDIT_PRODUCT=audit` in `.env`), granting to that product's owner, developer and writer roles

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
How should `lakehouse_starrocks.connect()` log people in from Jupyter (people use LDAP passwords in StarRocks today)?

A) Ask for the user's StarRocks (LDAP) password with `getpass` each time a connection is opened in the kernel; never stored or logged

B) Same, but keep the password in the kernel's memory for the session after the first prompt

C) Switch people to token login (Keycloak) in StarRocks so Jupyter can use the user's token; this changes how every person logs in to StarRocks (DBeaver and JDBC included)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
When should the plugin, the staging database and table, and the `srv-auditloader` user be put in place?

A) In the StarRocks bootstrap on every `scripts/lakehouse.sh start` (idempotent: create or check, install if missing), and checked by `status`

B) Only by a separate command (for example `scripts/lakehouse.sh install-starrocks-audit`) run once by the admin

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
What else belongs in this intent?

A) Commit `data-products/audit.yaml` (as applied), and update the docs (StarRocks reference, data products reference, security, operations) and canonical knowledge

B) Only the capture, grants and helper; `audit.yaml` and docs separately

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question: Resiliency Extensions
Should the resiliency baseline be applied to this project?

**What this extension is.** Enabling it applies a set of **directional, design-time best practices** for building resilient systems, derived from the **AWS Well-Architected Framework (Reliability Pillar)** and resilience-review guidance. It steers requirements, design, and code toward fault tolerance, high availability, observability, and recoverability — covering 15 practice areas across business goals, change management, observability, high availability, disaster recovery, and continuous improvement.

**What this extension is NOT.** Enabling it does **not** make your workload production-ready, nor does it certify or guarantee any availability, RTO, or RPO target. It is a **starting point** that scaffolds good resiliency decisions early — it is not a substitute for a formal **AWS Well-Architected Review** of the built system.

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that you can validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
