# Jenkins

Reference: CI for each data product's repository. Back to the [README](../../README.md).

Jenkins runs CI for each data product in a folder named after the product (`default` for the default product). With a `repo` block, the folder holds two multibranch pipelines on the repository's `Jenkinsfile`:

| Job | Builds | Source | Checks for changes |
|---|---|---|---|
| `<name>_ci` | `prod_branch` and `uat_branch`, when they get new commits | Git, anonymous | every 5 minutes |
| `<name>_cd` | every branch of the repository that is the source of an open pull request; forks are not built | GitHub, anonymous (github.com repositories only) | every 30 minutes |

- **Builds**: on the built-in node, without the Docker socket. There are no webhooks, so changes are picked up by the scheduled scans; **Scan Multibranch Pipeline Now** checks right away. A branch whose pull request closes, or that leaves the filter, is removed with its build history.
- **GitHub limit**: without a token, GitHub allows 60 API requests per hour for this machine. Each `_cd` scan uses a few, so about five products with a GitHub `repo` fit. A repository on another host gets only `<name>_ci`.
- **Folders and jobs as code**: `render_jenkins.py` writes the folders, their permissions, and the jobs as a Job DSL script (`.runtime/container-mounts/jenkins-jobs.groovy`) and the expected set (`jenkins-products.json`). At every start, also after a reset, the hook `infra/jenkins/init.groovy.d/reconcile-data-products.groovy` applies the script, then deletes the managed folders and jobs that left the product files; it never touches other items. Edits made in the UI to the folders and jobs are overwritten at the next start; jobs that owners add to their folder are kept.
- **Sign-in**: through Keycloak, with permissions as in [Identity — what each group can do](identity.md#what-each-group-can-do).
- **The repository's checks**: `lakehouse-validate-workflows` (workflows, the `dags/` stub, `requirements.txt` against the platform lock) is on the Jenkins image; the rest is the product repository's own `Jenkinsfile`.

## Configuration

- **Plugins**: the image pins exactly the plugins in `infra/jenkins/plugins.txt`.
- **Security as code**: `infra/jenkins/casc/jenkins.yaml` is the template for the security realm, the project-based matrix, and the break-glass account. `infra/products/render_jenkins.py` adds the product groups, folders, and jobs and writes `.runtime/container-mounts/jenkins-casc.yaml`, which Jenkins applies at every start. UI changes to these are overwritten.
- **Build history**: it lives in the volume `lakehouse-local_jenkins-home` and is lost on a reset.
- **Break-glass**: if Keycloak is down, use the escape-hatch login as `jenkins-break-glass`. The password is in `.runtime/credentials/jenkins-break-glass-password`.
