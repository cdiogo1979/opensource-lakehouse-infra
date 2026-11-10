# Intent Summary: Polaris Database Path Layout

## Objective
Use catalog identifiers `lakehouse`, `lakehouse_uat`, and `lakehouse_dev` and resolve table objects beneath `<bucket>/<catalog>/<database>/<table>` without repeating the database segment.

## Outcome
Updated Polaris and Spark bootstrap/configuration, executed the user-approved one-time local reset, recreated the three catalogs/namespaces and smoke tables, verified exact object paths and all four role matrices, and confirmed normal bootstrap reruns preserve objects. Prepared a deploy handoff; no external deployment or pull request was performed.

## Verification
Static validation, local provider bootstrap, Spark create/readback/vended credential checks, developer/analyst/owner/writer matrix, temporary-resource cleanup, and non-destructive bootstrap rerun passed. Full evidence is copied under `full-artifacts/aidlc-docs/current/`.

## Archived Artifacts
The full prior current workflow documents, README, touched Polaris and Spark source files, and canonical application design were copied under `full-artifacts/`. The original active current documents remain preserved in the archived snapshot.
