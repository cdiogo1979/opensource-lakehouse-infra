# Requirements Clarification — Cross-Client RBAC

Your custom answer sets the goal that a user should have consistent access to the same files when using Dremio, Jupyter, or RustFS directly. The current Compose project has no Jupyter service. Dremio Community supports local user identities, while its current edition matrix does not list external identity providers or RBAC as Community features. RustFS S3 access is separately authorized through S3 identities and policies. Please select the intended PoC boundary and authorization model.

## Question 1 — Jupyter boundary
How should Jupyter be included?

A) Add a Jupyter service to this Compose PoC and configure user access for the demonstration

B) Connect this PoC to an existing Jupyter/JupyterHub environment; document its required setup and integration

C) Do not include Jupyter in the running PoC yet; document it as a future integration target

X) Other (please describe after `[Answer]:` below)

[Answer]: X, yes add jupyter , taking as base the setup already in place in the jupyter-platform folder 

## Question 2 — Shared authorization behavior
What does “the same files” mean for the RBAC demonstration?

A) Two users/groups have different RustFS object-prefix permissions, and the allowed/denied read behavior must be consistent through Dremio, Jupyter, and direct S3 access

B) Users have Hive database/table permissions; direct RustFS access is out of scope or denied, so users cannot bypass Hive/Dremio authorization

C) Demonstrate both table-level and object-prefix authorization, with matching grants and denials across the three access paths

X) Other (please describe after `[Answer]:` below)

[Answer]: X, whateever is simple to demonstrate simple access/no access to a given database (from jupyter/spark + dremio )

## Question 3 — User identity mapping across services
Which identity model should the PoC use to make authorization decisions consistent?

A) Keep Dremio Community local users and the disposable Kerberos realm. Create matching usernames/groups in Hive and RustFS, and use separate per-user RustFS S3 credentials/policies for direct storage access and Jupyter

B) Allow a central identity provider and/or Dremio edition change if needed so Dremio, Jupyter, and RustFS can authenticate the same users through supported federation

C) Use Dremio/Hive per-user impersonation, but use shared RustFS service credentials for Jupyter and direct access; document that storage-level identity is not consistent across paths

X) Other (please describe the desired user, group, and credential flow after `[Answer]:` below)

[Answer]:A

## Question 4 — RBAC acceptance scenario
Which minimum demonstration should be required?

A) Two users: one is allowed to read a designated dataset/prefix and the other is denied, with the allow/deny result shown through each in-scope access path

B) A single user/group with a positive access check through each in-scope path; no negative check

C) A different user/group and dataset scenario that I will specify

X) Other (please describe after `[Answer]:` below)

[Answer]: A

## Reference notes

- [Dremio editions](https://docs.dremio.com/editions/) lists Hive Metastore and local identities for Community; external identity providers and Role-Based Access Control are listed as Enterprise features.
- [Dremio Hive source configuration](https://docs.dremio.com/current/data-sources/lakehouse-catalogs/hive/) documents Hive source impersonation settings.
- [RustFS S3 protocol](https://docs.rustfs.com/content/en/administration/protocols/s3.md) documents S3 access/secret credentials and IAM policies.
