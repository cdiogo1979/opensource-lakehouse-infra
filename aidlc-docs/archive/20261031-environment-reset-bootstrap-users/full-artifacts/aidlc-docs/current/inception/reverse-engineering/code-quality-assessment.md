# Code Quality Assessment — Reset and Identity Bootstrap

- **Tests**: contract tests exist for the Keycloak clients and the Compose wiring. There are none yet for user bootstrap or a reset.
- **Technical debt**:
  - `joe-developer` was created by hand.
  - `platform-admin` uses a random temporary password from a file, which is not the requested shared default.
  - Airflow maps developer to `User` while its tests expect `Admin` (pre-existing drift).
- **Risks**:
  - A full reset is irreversible: it destroys buckets, catalogs, users, Jenkins history, Airflow metadata, and secrets.
  - A shared default password (`ChangeM3!`) is weak unless it is forced to change.
