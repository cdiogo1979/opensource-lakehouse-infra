# Requirements Clarification — Jupyter Identity and Access Paths

Inspection of `jupyter-platform/` found JupyterHub 5.3.0 with DockerSpawner and one Spark single-user container per Hub user. The current setup uses DummyAuthenticator, runs notebook containers as the shared OS account `jovyan`, and gives every user the same RustFS admin credentials and Nessie catalog settings. The answers below determine the minimum changes needed for the requested per-user access demonstration.

## Question 1 — Direct RustFS access in the RBAC demonstration
Should the allow/deny result also be demonstrated by accessing RustFS directly through its S3 API?

A) Yes. Include Dremio, Spark in each Jupyter user container, and direct RustFS S3 requests; use per-user S3 identities/policies so direct access has its own allow/deny check.

B) No. Limit the demonstration to access to a Hive database through Dremio and Spark in Jupyter; direct RustFS access is outside the demonstration.

X) Other (please describe after `[Answer]:` below)

[Answer]: B

## Question 2 — JupyterHub user authentication
The current DummyAuthenticator accepts any username and password, so a user can claim another user's name. How should the local demo authenticate its two test users?

A) Replace DummyAuthenticator with local password-backed JupyterHub accounts for the test users.

B) Keep DummyAuthenticator and treat usernames only as development labels, not verified identities; this limits the RBAC result to a functional demo.

C) Connect JupyterHub to an existing identity provider; I will provide the configuration requirements.

X) Other (please describe after `[Answer]:` below)

[Answer]: B

## Question 3 — Kerberos identity for Spark in Jupyter
How should Spark jobs started from a user's notebook authenticate to Hive and apply that user's access rules?

A) Generate a distinct Kerberos principal/keytab for each test user in the disposable KDC initialization, mount only that user's keytab read-only into their notebook container, and have their Spark session authenticate as that principal.

B) Use one Spark service principal for all notebook containers; demonstrate per-user access only through Dremio, not Spark in Jupyter.

C) Use a shared Spark service principal and Hadoop proxy-user/doAs rules to represent the authenticated Jupyter username; do not mount per-user keytabs.

X) Other (please describe after `[Answer]:` below)

[Answer]: A

## Question 4 — Authorization demonstration scope
Which resource and access paths should the two-user allow/deny scenario cover?

A) One Hive database with two test users: one can read it and the other is denied through Dremio and Spark in Jupyter; if Question 1 includes direct RustFS, also verify per-user access to the underlying object prefix.

B) One Hive database with different table-level permissions; test both allowed and denied table access through Dremio and Spark in Jupyter.

C) One object-store prefix only; test allowed/denied access through Spark and direct S3, while Dremio consumes the same tables using its source identity.

X) Other (please describe after `[Answer]:` below)

[Answer]: X two databases , one user can only access databaseA and the other bothe databases
