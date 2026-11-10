# Functional Design — Jenkins CI and Access

Current functional design of the v2 Jenkins component. For architecture, see [`../application-design.md`](../application-design.md). History is in the [Data Product Jenkins Pipelines intent archive](../../../archive/20261110-data-product-jenkins-pipelines/intent-summary.md), the [Jenkins Onboarding and Keycloak SSO intent archive](../../../archive/20261031-jenkins-keycloak-sso/intent-summary.md), and the [Data Product and User Scripts intent archive](../../../archive/20261109-data-product-and-user-scripts/intent-summary.md).

## Responsibility
Jenkins runs the CI for each data product's repository.
- **Folder**: every product has a top-level folder `<name>`. Its description ends with the marker `Managed by the lakehouse data product files.`
- **Jobs**: with a `repo` block, the folder holds two multibranch pipelines on the repository's root `Jenkinsfile`. They run on the built-in node (2 executors), without the Docker socket or webhooks.

| Job | Source | Builds | Scan |
|---|---|---|---|
| `<name>_ci` | plain Git, `repo.url`, anonymous | exactly `repo.prod_branch` and `repo.uat_branch` (wildcard filter, deduplicated) | every 5 minutes |
| `<name>_cd` | GitHub Branch Source, anonymous; only for `https://github.com/<owner>/<repository>[.git][/]` | same-repository branches that are the source of an open pull request (`strategyId 2`); no PR-head or fork discovery | every 30 minutes |

- **Branch jobs**: both jobs prune orphaned branch jobs with their history (`discardOldItems`), for example when a PR closes or a branch leaves the filter.
- **Non-GitHub repository**: it gets only `_ci`, and the render prints why.
- **Product without `repo`**: an empty folder, with the owner as admin.
- **Rate limit**: unauthenticated GitHub allows 60 API requests per hour for the machine, which at the 30-minute `_cd` scan is about five products.
- **Other repositories**: there is no job for this infrastructure repository. The pre-2026-10-31 job `opensource-lakehouse-dp/opensource-lakehouse-ci` was retired; `default/default_ci` and `default/default_cd` replace it.

## Access rules
The authorization strategy is the project-based matrix (`projectMatrix`).

| Keycloak group / identity | Global | On the product's folder (inherited by its jobs) |
|---|---|---|
| `role-platform-admin` | `Overall/Administer` | everything |
| `jenkins-break-glass` (escape hatch) | `Overall/Administer` | everything |
| `role-<name>-owner` | `Overall/Read` | `FOLDER_ADMIN_PERMISSIONS` (22): Credentials Create, Delete, ManageDomains, Update and View; Job Build, Cancel, Configure, Create, Delete, Discover, Move, Read and Workspace; Run Delete, Replay and Update; SCM Tag; View Configure, Create, Delete and Read |
| roles in `apps.jenkins` (default: developer `Job/Read`, `Job/Build`, `Job/Cancel`, `Job/Workspace`; analyst `Job/Read`) | `Overall/Read` | their listed permissions |
| writer groups (unless listed), users without a group, anonymous | none | none |

- **Product file rules**:
  - `apps.jenkins` accepts `developer`, `analyst` and `writer`, with non-empty lists drawn from the folder set.
  - `owner` is refused, because the owner is always the folder admin.
  - Any `Overall/*` permission is refused.
  - A product group may not reuse a static entry's name.
- **Isolation**: a product's members can't see another product's folder (404). Verified live in both directions.
- **Authorities**: group names arrive as plain values of the ID-token `groups` claim, and a user in several groups receives the union.
- **Sign-in**: people sign in through the Keycloak `jenkins` client only. The legacy local user database is not a login path.
- **Escape hatch**: `jenkins-break-glass`, with a protected password file stored BCrypt-hashed. It works while Keycloak is down, including for basic-auth API calls.

## Configuration authority
`infra/products/render_jenkins.py` renders three deterministic files into `.runtime/container-mounts/`:

| File | Mounted at | Content |
|---|---|---|
| `jenkins-casc.yaml` | `/var/jenkins_casc/jenkins.yaml` | the template `infra/jenkins/casc/jenkins.yaml` (OIDC realm, `projectMatrix` with the static entries, escape hatch, executors, mode, crumb issuer, root URL), plus `Overall/Read` for each product group |
| `jenkins-jobs.groovy` | `/run/lakehouse/jenkins-jobs.groovy` | the Job DSL script: one `folder` per product (description, `authorizationMatrix` with `inheriting()` and the group entries), plus the jobs |
| `jenkins-products.json` | `/run/lakehouse/jenkins-products.json` | the expected set, `{"<name>": ["<name>_ci", "<name>_cd"]}` |

- **Reconcile hook**: `infra/jenkins/init.groovy.d/reconcile-data-products.groovy` is mounted read-only into the home's `init.groovy.d`. At every start, after Jenkins has loaded its jobs, it:
  1. applies the Job DSL script (`DslScriptLoader`, `JenkinsJobManagement`), creating or updating folders and jobs;
  2. deletes the marked top-level folders missing from the state (with everything in them), and, in listed folders, the unlisted `<name>_ci` and `<name>_cd` jobs.

  It deletes nothing when the apply fails or the state is missing, unreadable, empty or not an object. Unmarked items, and jobs that owners create inside their folder, are never touched.
- **Why not CasC `jobs:`**: CasC runs Job DSL before Jenkins loads its jobs, so a newly created folder was dropped from memory until the next restart (found 2026-11-10).
- **When it renders**: on every `lakehouse.sh start` (through `prepare-runtime.py`), and on every product apply or removal.
  - **Restarts**: Jenkins restarts only when one of the three files changed; `--no-restart` prints the command instead. Files are rewritten in place, because single-file bind mounts keep their inode.
  - **Plan**: `render_jenkins.py --check` and `--dry-run` print the folders and jobs to create or delete.
  - **Invalid product files**: the render refuses, and the running Jenkins keeps its files.
- **Quoting**: every product value in the DSL is a single-quoted Groovy literal (`\`, `'` and newlines escaped, non-printable characters refused). The DSL file is not read by CasC, so `${...}` in a description stays literal.
- **UI edits**: changes to the managed folders and jobs are overwritten at the next start.
- **Plugins**: `infra/jenkins/plugins.txt` holds 105 exact versions, including `job-dsl 3732.v9a_c49a_61a_313`, `oic-auth`, `matrix-auth 3.3`, `github-branch-source` and `cloudbees-folder`. The image build compares `name:version` from every plugin manifest with the list and fails on any difference. `PLUGINS_FORCE_UPGRADE=true` makes the image authoritative.
- **Workflow validator**: `lakehouse-validate-workflows [ROOT]` (`infra/jenkins/bin/`, mounted read-only at `/usr/local/bin/`) runs the platform's `lakehouse_dags.validate` from the read-only package mount `/opt/lakehouse/python/lakehouse_dags`. Product `Jenkinsfile`s call it in a "Validate workflows" stage; it checks `workflows/*.json`, the exact `dags/lakehouse.py` stub, and that `dags/` holds nothing else (see `airflow-workflows.md`).
- **Secrets**: the client secret and the break-glass password come from mounted files. Nothing secret is in configuration as code, Compose, the container environment, the DSL or the jobs. Repositories are read anonymously.

## Home
- **Location**: Jenkins runs from `compose.jenkins.yml` (unless `JENKINS_ENABLED=false`) with its home in the named volume `lakehouse-local_jenkins-home`.
- **New home**: a new volume is filled from the image, and the hook recreates every folder and job at the first start.
- **Build history**: it lives only in the home. A `reset` deletes it. Removing a product deletes its folder's history, and removing its `repo` deletes the history of the two jobs.
- **Pre-reset backup**: `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz` is no longer needed to restore jobs.

## Failure behavior
- **Keycloak unavailable**: SSO logins fail, the escape hatch works, and builds continue.
- **Plugin mismatch at image build**: the build fails.
- **Job DSL failure at start**: logged as SEVERE (`not applied; nothing deleted`). Jenkins starts with its previous folders and jobs.
- **GitHub rate limit exhausted**: `_cd` scans wait for the limit to reset. `_ci` needs no GitHub API.

## Verification and known limits
- **Verified 2026-11-10** (Data Product Jenkins Pipelines):
  - `jenkins-oidc.py` 10/10, including the project matrix and the product folder check (marker, the owner's full admin set by permission class, exact jobs, no stale managed folder);
  - `default_ci` `main` #1 and `uat` #1 SUCCESS, and `default_cd` scanned unauthenticated;
  - the ACL for each group, with cross-product isolation;
  - `jptest`: created, `repo` removed (jobs deleted, folder kept), removed (folder deleted), re-created from scratch (in memory after one start, builds SUCCESS), re-applied unchanged (no restart).
- **Not run**: a `_cd` build of a real PR (none open), a `reset`, interactive per-role browser logins.
- **Earlier**: the 2026-10-31 SSO verification covered the escape hatch, logout, plugin parity, restart and an interactive login.
- **Limits**:
  - no webhooks;
  - unauthenticated GitHub only, with no fork PRs;
  - builds run on the built-in node without isolation;
  - pipelines needing Docker are not supported;
  - back up `lakehouse-local_jenkins-home` before a reset if the build history matters.
