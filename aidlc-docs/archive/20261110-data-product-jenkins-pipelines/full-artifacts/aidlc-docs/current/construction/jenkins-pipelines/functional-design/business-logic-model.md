# Functional Design — jenkins-pipelines

## Business rules
- **BR-1 Folder**: every product gets a folder named `<name>`.
  - **Description**: the product description, a blank line, then the marker `Managed by the lakehouse data product files.`
  - **Authorization**: `inheriting()`. Folder entries:
    - owner group: `FOLDER_ADMIN_PERMISSIONS`;
    - every other role in `apps.jenkins`: its permissions.
- **BR-2 `FOLDER_ADMIN_PERMISSIONS`** (22): `Credentials/Create`, `Credentials/Delete`, `Credentials/ManageDomains`, `Credentials/Update`, `Credentials/View`, `Job/Build`, `Job/Cancel`, `Job/Configure`, `Job/Create`, `Job/Delete`, `Job/Discover`, `Job/Move`, `Job/Read`, `Job/Workspace`, `Run/Delete`, `Run/Replay`, `Run/Update`, `SCM/Tag`, `View/Configure`, `View/Create`, `View/Delete`, `View/Read`.
- **BR-3 Product file `apps.jenkins`**:
  - **Keys**: `developer`, `analyst`, `writer`. `owner` is refused: "the owner is always admin of the product folder".
  - **Values**: non-empty lists from `FOLDER_ADMIN_PERMISSIONS`. `Overall/*` is refused: "global Jenkins rights are not granted by product files".
  - **Global read**: the owner group and every listed role's group get `Overall/Read` globally. Nothing else is granted globally to a product group.
  - **Static entries**: `role-platform-admin` and `jenkins-break-glass` keep `Overall/Administer`. A product group may not reuse a static name.
- **BR-4 Jobs**: only for a product with `repo`.
  - **`<name>_ci`**: `git` source `repo.url`, id `<name>_ci`, `gitBranchDiscovery`, wildcard includes `"<prod_branch> <uat_branch>"` (deduplicated when the two are equal). Branch names can't contain spaces or `*`, because `BRANCH_PATTERN` excludes them. Trigger every 5 minutes; `discardOldItems`; `Jenkinsfile`.
  - **`<name>_cd`**: only when `github_repository(repo.url)` returns `(owner, repository)`. `github` source, id `<name>_cd`, `repositoryUrl` set to `https://github.com/<owner>/<repository>`, `strategyId(2)`, no PR or fork discovery. Trigger every 30 minutes; `discardOldItems`; `Jenkinsfile`.
  - **Non-GitHub URL**: the render prints `<name>: no <name>_cd job (pull request discovery needs a github.com repository)`.
- **BR-5 `github_repository(url)`**: matches only `https://github.com/<owner>/<repository>` with an optional `.git` or `/`, where the owner is `[A-Za-z0-9-]{1,39}` and the repository is `[A-Za-z0-9._-]{1,100}` and isn't `.` or `..`. Anything else returns `None`.
- **BR-6 Reconcile hook** (at every start, after the jobs load):
  - **Apply first**: it applies `/run/lakehouse/jenkins-jobs.groovy` with Job DSL. If that fails, it logs an error and deletes nothing. (Changed in Build and Test: the DSL ran from CasC before, where new folders were lost until the next restart.)
  - **When it skips**: if the state file is missing, unreadable, not a JSON object, or an object with no products, it logs a warning and deletes nothing.
  - **Top-level folders** with the marker in their description:
    - not in the state: the folder is deleted, with everything in it;
    - in the state: each of `<name>_ci` and `<name>_cd` that isn't listed is deleted.
  - **Never touched**: anything else, including unmarked folders, non-folder items, other children, and nested items.
  - **Logging**: each deletion is logged.
- **BR-7 State JSON**: `{"<name>": ["<name>_ci", "<name>_cd"]}`, keys in product order, jobs in this order. Written with sorted keys off, 2-space indent and a trailing newline, so the output is deterministic.
- **BR-8 Plan (`--check`, dry run)**: compares the desired state with the current state file, if any. It prints `create folder`, `create job`, `delete job (with build history)`, `delete folder (with jobs and build history)`, or `Jenkins folders and jobs unchanged`. Permission changes are reported as `Jenkins configuration would change`.
- **BR-9 Quoting**: every product-derived value in the Job DSL (description, URL, branches, owner, repository, group names) passes through `groovy_string()`. That gives a single-quoted Groovy literal with `\`, `'` and newline escaped, and non-printable characters refused. `$` needs no escape in single quotes.
- **BR-10 Change and restart**: the three files (CasC, Job DSL, state) are written in place. Exit 3 if any changed, and `apply_jenkins` restarts a running Jenkins only then. An unchanged reapply means no restart, so jobs and history aren't touched.

## Testable properties (PBT partial)
| Id | Rule | Property |
|---|---|---|
| P1 (PBT-02) | BR-9 | For generated printable text, including quotes, backslashes, `$`, newlines and non-ASCII: parsing `groovy_string(s)` back as a Groovy single-quoted literal gives `s`. |
| P2 (PBT-03) | BR-1, BR-3 | For generated product sets: each folder's entries name only that product's groups. The owner's permissions equal `FOLDER_ADMIN_PERMISSIONS`. Product groups hold globally exactly `["Overall/Read"]`. The static admins are present. |
| P3 (PBT-02, PBT-03) | BR-4, BR-7 | The folders and jobs parsed back from the rendered DSL equal `desired_items()`, which equals the state JSON loaded back. `_cd` is present exactly when `repo` is set and the URL is on GitHub. |
| P4 (PBT-03) | BR-10 | Rendering is deterministic: the same input gives the same bytes for both files. |
| P5 (PBT-03) | BR-5 | Generated GitHub URLs, with or without `.git` or `/`, map to their owner and repository. Generated non-GitHub hosts map to `None`. |

Generators: `tests/products/product_strategies.py` (`product_sets`, `repo_urls`), extended with GitHub URL shapes (PBT-07). Hypothesis with the default shrinking and `print_blob=True` (PBT-08, PBT-09).

## Hook contract checks (example-based)
- The hook reads only the state path, compares descriptions against the exact marker, deletes only `Folder` top-level items and the `_ci` and `_cd` children by exact name, and has the empty, missing or invalid-state guard.
- The live check in Build and Test covers the deletions.
