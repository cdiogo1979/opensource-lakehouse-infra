# Requirement Verification Questions — Data Product Jenkins Pipelines

Answered interactively on 2026-11-10. Answer each question after its `[Answer]:` tag with a letter, or with X and your own text. The background is in `../reverse-engineering/jenkins-product-pipelines.md`.

## Q1 How the folder and jobs are created
Jenkins jobs aren't configuration as code today, and the 2026-10-31 reset deleted them.

A) Job DSL in the rendered CasC file: add the pinned `job-dsl` plugin; `render_jenkins.py` writes one folder and two jobs per product. Jenkins recreates them at every start and after a reset. A removed product's folder gets one explicit delete. (Recommended)

B) Jenkins REST API from the operator scripts (`createItem` with `config.xml`), signed in as the break-glass account. No new plugin, but it works only while Jenkins runs, and a reset loses the jobs.

X) Other (please describe after [Answer]: tag below)

[Answer]: A — Job DSL in the rendered CasC file

## Q2 The owner's rights
"Admin of the top folder" means switching Jenkins to the project-based matrix. The owner's platform-wide `Overall/Administer` would otherwise override every folder.

A) Folder admin only: the owner group gets every job, run, view, SCM and credential permission on its product folder, including configuring and deleting jobs and adding folder-level credentials, plus `Overall/Read` globally. Only `role-platform-admin` and break-glass stay Jenkins administrators. (Recommended)

B) Both: the folder rights in A, and the owner keeps `Overall/Administer` on the whole Jenkins, as today.

X) Other (please describe after [Answer]: tag below)

[Answer]: A — folder admin only

## Q3 Developers' and analysts' rights
Their `apps.jenkins` rights (developer: read, build, cancel, workspace; analyst: read) apply to all of Jenkins today.

A) Scope them to their own product's folder; globally they keep only `Overall/Read`. A developer of `sales` can't see or build `default` jobs. (Recommended)

B) Keep them platform-wide, as today.

X) Other (please describe after [Answer]: tag below)

[Answer]: A — own folder only

## Q4 GitHub API access for the `_cd` (pull request) job
Only the GitHub API can list a repository's PRs. Without a token, GitHub allows 60 requests per hour for this machine, and every scan uses several.

A) Optional, platform-wide, read-only GitHub token: if `.runtime/credentials/jenkins-github-token` exists, it's mounted as a Jenkins credential and used by every `_cd` job (5,000 requests per hour). Without it, the jobs scan unauthenticated and the scripts warn about the limit. The `repo` block stays free of credentials. (Recommended)

B) Unauthenticated only, with a longer `_cd` scan interval to stay under the limit.

C) Require the token: no token, no `_cd` jobs.

X) Other (please describe after [Answer]: tag below)

[Answer]: B — unauthenticated only (with a longer _cd scan interval)

## Q5 Pull requests from forks
The `_cd` job builds the source branch of each open PR, on the built-in Jenkins node, without isolation.

A) Same-repository PR branches only. Fork PRs are ignored, so outside code never runs on Jenkins. (Recommended)

B) Also build fork PRs.

X) Other (please describe after [Answer]: tag below)

[Answer]: A — same-repository PR branches only

## Q6 How often Jenkins checks for changes
Jenkins is loopback-only and gets no webhooks, so it checks for changes by scanning on a schedule.

A) `_ci` every 5 minutes, like Airflow's bundle refresh. `_cd` every 5 minutes with a token, or every 30 minutes without one. (Recommended)

B) Both every 5 minutes, always.

C) Both every 15 minutes.

X) Other (please describe after [Answer]: tag below)

[Answer]: _ci every 5 minutes, _cd every 30 minutes (asked again for the unauthenticated case)

## Q7 Products without a `repo` block
A) No folder and no jobs. Adding `repo` later and reapplying creates them. (Recommended)

B) An empty folder with the owner as admin, and jobs only once `repo` is set.

X) Other (please describe after [Answer]: tag below)

[Answer]: B — an empty folder with the owner as admin; jobs only once repo is set

## Q8 What removal does with the folder
`remove-data-product.sh` already asks for the typed product name and backs up the product file.

A) Delete the folder, its jobs and their build history, after the existing confirmation. Removing only the `repo` block from a product deletes its folder the same way. (Recommended)

B) Disable the jobs and keep the folder and its history; an administrator deletes it later.

X) Other (please describe after [Answer]: tag below)

[Answer]: A — delete the folder, jobs and history after the existing confirmation. Clarified with Q7: removing only repo deletes the two jobs and their history and keeps the empty folder; removing the product deletes the folder

## Q9 The old `opensource-lakehouse-dp/opensource-lakehouse-ci` job
A) Don't restore it. The `default` product gets `default/default_ci` and `default/default_cd` from its `repo` block. The verifier and README now expect those, and the Jenkins CI job follow-up closes. (Recommended)

B) Restore it from the backup as well, alongside the new jobs.

X) Other (please describe after [Answer]: tag below)

[Answer]: A — don't restore it

## Q10 Extensions
A) Property-based testing, partial (PBT-02, 03, 07, 08, 09), for example on the rendering of folders, jobs and permissions. Security and Resiliency off. (Recommended)

B) All off.

C) Partial property-based testing plus the Security baseline.

X) Other (please describe after [Answer]: tag below)

[Answer]: A — PBT partial (PBT-02, 03, 07, 08, 09); Security and Resiliency off
