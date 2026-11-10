# User Story Generation Plan

## Purpose

Turn the approved requirements for FreeIPA identities, environment-scoped RustFS access, Hive/Spark authorization, JupyterHub login, and StarRocks/Ranger policies into user-valued outcomes with independently verifiable acceptance criteria.

## Recommended personas

- **Platform identity administrator**: creates users, groups, and service identities in FreeIPA and manages lifecycle/cutover.
- **Developer**: uses JupyterHub and Spark to read all environments and write development data only.
- **Analyst**: uses JupyterHub and StarRocks to read production data without write access.
- **ETL workload owner**: operates workloads using `write-service-account` to write all approved environments.
- **Lakehouse operator**: runs the platform and verifies bucket, database, query, and identity health.

## Recommended organization

Use feature-based stories grouped by:

1. Central identities and group lifecycle.
2. Environment buckets and database locations.
3. Direct Spark/RustFS authorization.
4. JupyterHub authentication and Spark Kerberos access.
5. StarRocks authorization through Ranger.
6. Safe replacement of `user_a`/`user_b` and preservation of `admin` privileges, production objects, and the writer's RustFS S3 key; reissue its Kerberos keytab under FreeIPA.

This keeps the different enforcement points visible while linking the user journey from FreeIPA account creation through login and data access.

## Acceptance-criteria style

Use concise, independently checkable criteria. Include both allowed and denied access for each principal and environment, service startup/readiness, migration safety, and explicit limits where Ranger does not govern direct Spark-to-RustFS access.

## Scope rules

- Stories describe outcomes, not implementation tasks or container wiring.
- Map each story to one or more requirement sections and an identified persona.
- Preserve existing `lake` objects and the writer's RustFS S3 key; Kerberos service keytabs are reissued under FreeIPA.
- Treat `write-service-account` as non-interactive; it is not a JupyterHub user.
- Distinguish UI login, Kerberos ticket acquisition, object-store permissions, Hive metadata permissions, and StarRocks query authorization.
- Do not claim a single policy engine enforces all access paths. RustFS IAM remains the object-store enforcement point; Ranger is used for the StarRocks integration supported by the deployed version.
- Do not start implementation or service changes as part of story generation.

## Approval

Approved by the user on 2026-10-27. Generated `inception/user-stories/personas.md` and `inception/user-stories/stories.md`. No runtime or service configuration was changed. Any additional requirement discovered during story generation is recorded as a clarification rather than silently changing the approved requirements.
