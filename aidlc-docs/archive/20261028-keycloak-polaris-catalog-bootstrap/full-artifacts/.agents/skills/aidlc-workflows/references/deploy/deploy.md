# Deploy

## Purpose

Prepare a reviewable PR request and deployment handoff after Build and Test. This is the final delivery-preparation stage before artifact compaction and intent closure.

The Deploy stage documents work; it does not open a pull request, deploy assets, execute notebooks, or make changes in any environment. Approval of its documents is not authorization to perform those actions.

## Inputs

Review the approved requirements and plans, implementation summary, Build and Test summary, changed source/configuration files, job definitions, and any existing `ops/` or `deploy/` notebooks. Derive ordering from explicit dependencies and project guidance. Do not assume a universal order for migrations, views, jobs, or pipeline runs.

## Required output: PR request

Always create `aidlc-docs/current/deploy/pr_request.md`. Use the exact filename so the handoff can be found consistently. Include:

- **Problem**: the user or system need this change addresses.
- **Solution**: the implemented approach and important design decisions.
- **Main changes**: concise paths/components and behavior changed.
- **Verification**: build/test results, what was not run, and any accepted verification waiver. A waiver is never presented as a pass.
- **Deployment**: whether ordered deployment steps are required and link to `deploy_instructions.md` when it exists.
- **Risks and limitations**: known compatibility, data, security, or operational concerns and required follow-up.

Write it as a proposed PR description. Do not claim a PR was created, merged, or approved. Avoid secrets and sensitive environment values.

## Conditional output: deployment instructions

Create `aidlc-docs/current/deploy/deploy_instructions.md` only when the change requires environment deployment or operational actions. Examples include Databricks Bundle/asset deployment, running data migration or patch notebooks under `notebooks/<project>/ops/`, deploying views or other assets through `notebooks/<project>/deploy/`, and required post-deployment pipeline or validation runs. If none are needed, omit this file and state that in `pr_request.md`.

When created, list steps in explicit execution order. For each step record:

1. **Action and target**: asset, notebook, job, environment, catalog/schema, or other target. Mark unknown values as required inputs; do not guess.
2. **Prerequisites**: approvals, permissions, backups, maintenance windows, configuration, and dependency steps.
3. **Execution**: exact repository path and command or UI action where known. For notebooks, specify the notebook path and required parameters.
4. **Validation**: expected observable outcome and how to verify it.
5. **Failure handling**: stop conditions and rollback/recovery guidance where known. Do not invent a safe rollback when none is designed; call it out as a blocker.

Order schema/data migrations before dependent assets or pipeline runs only when the design and dependencies require that order. Keep `ops/` migration or patch notebooks distinct from `deploy/` asset notebooks and list each in its required sequence. State which steps are manual and which are automated.

## Unknowns and verification limitations

Do not block document preparation on unavailable deployment details. Record missing owners, environments, permissions, secret references, versions, windows, or rollback procedures as explicit blockers or inputs needed. Never expose secret values.

If Build and Test was waived, prominently list the unverified scope in both the PR request and deployment instructions. Label deployment as conditional on resolving required blockers and completing required validation. A waiver permits workflow closure when separately approved; it does not prove runtime behavior, authorize release, or make the change production-ready.

## Review gate and state

Present both generated files, or explain why deployment instructions were unnecessary. Ask the user to request changes or approve the Deploy handoff. Record the complete raw response in `aidlc-docs/current/audit.md` and update `aidlc-docs/current/aidlc-state.md`.

After Deploy handoff approval, intent closure remains a separate step: follow `references/common/artifact-compaction.md` only after passed verification or explicit acceptance of a documented verification waiver and separate closure approval. Include `aidlc-docs/current/deploy/` artifacts in the compaction inventory and archive; allow only this workflow directory to be cleaned after its contents have been archived.
