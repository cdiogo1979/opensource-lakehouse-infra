# Requirements — Data Product Jenkins Pipelines

## Intent Analysis
- **Request**: when a data product is created, also set up Jenkins. Each product gets a folder, and inside it two multibranch pipelines on the repository's `Jenkinsfile`:
  - `<name>_ci` builds the UAT and main branches when they change;
  - `<name>_cd` builds any branch that is the source of a pull request.

  The product owner is the folder's administrator.
- **Type**: enhancement of the data product apply flow and the Jenkins configuration, brownfield.
- **Scope**: the Jenkins image (one plugin), the Jenkins CasC template and renderer, the product model, the create and remove scripts, the verifier, tests, and the README.
- **Complexity**: moderate. The authorization model changes from platform-wide to per folder.
- **Depth**: standard.
- **Answers**: `requirement-verification-questions.md`, Q1 to Q10, answered interactively on 2026-11-10.

## Functional Requirements

### FR-1 Folder per product (Q7 B)
- Every applied product has a top-level Jenkins folder named `<name>`, whether or not it has a `repo` block.
- The folder lists the product's description. It holds only the jobs described in FR-2.

### FR-2 Two multibranch pipelines when `repo` is set
- **The pair**: a product with `repo` gets `<name>/<name>_ci` and `<name>/<name>_cd`. Both read `Jenkinsfile` at the repository root, on the built-in node.
- **`<name>_ci`**:
  - **Source**: plain Git, `repo.url`, anonymous.
  - **Branches**: exactly `repo.prod_branch` and `repo.uat_branch`, so they follow the product file rather than being fixed to `main` and `uat`.
  - **Trigger**: a scan every **5 minutes**, which builds a branch when its head commit changed (Q6). Without webhooks, "when they change" means this scan.
- **`<name>_cd`**:
  - **Source**: GitHub Branch Source, anonymous (Q4 B).
  - **Branches**: only same-repository branches that are the source of an open pull request, built at the branch head. Fork PRs are not discovered (Q5 A). A branch whose PR closes is pruned.
  - **Trigger**: a scan every **30 minutes**, to stay under GitHub's 60 unauthenticated requests per hour for this machine (Q6).
  - **GitHub only**: `_cd` needs a `repo.url` of the form `https://github.com/<owner>/<repository>[.git]`. For another host, only `_ci` is created and the apply reports why.
- **Names**: product names match `[a-z][a-z0-9]{1,19}`, so `<name>`, `<name>_ci` and `<name>_cd` are valid Jenkins item names and unique.

### FR-3 Jobs as configuration as code (Q1 A)
- Add the `job-dsl` plugin at an exact pinned version; plugin parity still holds.
- `infra/products/render_jenkins.py` renders the folders and jobs as a CasC `jobs:` Job DSL script into `.runtime/container-mounts/jenkins-casc.yaml`.
  - **Deterministic**: same product set, same bytes.
  - **Recreated at start**: Jenkins rebuilds the folders and jobs at every start, including after `reset`.
  - **Restarts**: the existing render-and-restart-when-changed flow (`apply_jenkins`) stays, with `--dry-run` and `--no-restart`.
- **No secrets**: the rendered file has no credentials, and the jobs use none.

### FR-4 Authorization per folder (Q2 A, Q3 A)
- **Strategy**: Jenkins switches from `globalMatrix` to `projectMatrix`.
- **Global entries**:
  - `role-platform-admin` and `jenkins-break-glass` keep `Overall/Administer`.
  - Each product role in `apps.jenkins` gets only `Overall/Read` globally.
- **Folder entries** (on the product's folder, inherited by its jobs and branches):
  - **Owner**: every item permission (job, run, view, SCM and credential permissions, including configure, create, delete and folder credentials), but no global administration.
  - **Developer and analyst**: their `apps.jenkins` job permissions, on their own folder only.
  - **Isolation**: a member of one product can't see or build another product's folder.
- **Product file schema**: `apps.jenkins` keeps its shape: role to permissions.
  - The template and `default.yaml` change the owner from `[Overall/Administer]` to the folder admin set.
  - `Overall/Administer` is no longer allowed in a product file; the validator explains why.
  - The allowed permission list is updated to the folder-level permissions.
- **Unchanged**: sign-in through Keycloak OIDC with group claims, and the break-glass login.

### FR-5 Create, change and remove (Q8 A)
- **Create or reapply**: renders the folder and, with `repo`, both jobs. Jenkins restarts only when the rendered file changed. A `repo` change (URL or branches) updates the jobs in place.
- **`repo` removed from a product**: deletes `<name>_ci` and `<name>_cd` with their build history and keeps the empty folder, so the owner stays its admin.
- **Product removal** (`remove-data-product.sh`, after its typed-name confirmation): deletes the folder with its jobs and build history.
- **Deletion mechanism**: CasC's Job DSL doesn't remove items that leave the script. The design must define how deletion is done: only items under folders the platform manages, never other jobs, and an outcome when Jenkins isn't running.
- **Dry run**: lists the folders, jobs and deletions that would happen.

### FR-6 The default product and the old job (Q9 A)
- **No restore**: the old `opensource-lakehouse-dp/opensource-lakehouse-ci` job is not restored. `default` gets `default/default_ci` and `default/default_cd` from its `repo` block.
- **Verifier**: `scripts/verify/jenkins-oidc.py`, or a new Jenkins jobs check, expects the product folders, the jobs, and the folder permissions instead of the old job.
- **Follow-up**: the "Jenkins CI job" follow-up closes when this intent closes.

### FR-7 Documentation and tests
- **README**:
  - the folder layout and the two jobs;
  - the scan intervals and the GitHub limit (about 5 products at 30 minutes);
  - GitHub-only `_cd`; no fork PRs;
  - the new per-folder rights (owners are no longer Jenkins administrators);
  - what removal deletes;
  - known limitations.
- **Knowledge docs**: `functional-design/jenkins-ci-access.md`, `lakehouse-product-access.md` and `application-design.md`.
- **Tests**: contract tests for the rendered CasC (authorization, folders, jobs, plugin pin) and Hypothesis properties under PBT partial (Q10 A).
- **Live check**:
  - the `default` folder and both jobs appear;
  - `default_ci` builds `main` and `uat`;
  - folder permissions hold for owner, developer, analyst and a member of another product;
  - a test product's folder is created, then deleted on removal.

## Non-Functional Requirements
- **NFR-1 Deterministic and idempotent**: rendering twice gives the same bytes. Reapplying an unchanged product doesn't restart Jenkins and doesn't change jobs or history.
- **NFR-2 No credentials**: no tokens, passwords or secrets in product files, the rendered CasC, job configuration, or logs. Every repository is read anonymously.
- **NFR-3 Least privilege**: only the platform admin and break-glass administer Jenkins. Product roles are confined to their folder.
- **NFR-4 Safe deletion**: only `<name>` folders the platform manages, and the `<name>_ci` and `<name>_cd` jobs inside them, can be deleted. Nothing else in Jenkins is touched.
- **NFR-5 Rate-limit awareness**: the `_cd` scan interval keeps unauthenticated GitHub use within about 60 requests per hour for up to about 5 products with a repo. This limit is documented.
- **NFR-6 Pinned**: the plugin set stays exact, and the image build fails on any mismatch.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q10: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q10: A) |
| Resiliency Baseline | No | Requirements Analysis (Q10: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Out of scope
- Webhooks, and exposing Jenkins outside loopback.
- GitHub tokens or any Jenkins credentials (Q4 B).
- Fork PRs (Q5 A).
- Build agents, Docker-based pipelines, and deployment steps in the workload `Jenkinsfile`.
- Restoring the old job's build history (Q9 A).
- Airflow changes.
