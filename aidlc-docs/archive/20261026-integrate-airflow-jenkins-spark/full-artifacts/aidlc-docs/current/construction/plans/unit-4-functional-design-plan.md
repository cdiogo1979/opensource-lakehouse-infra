# Unit 4 Functional Design Plan — Jenkins Validation

## Unit Context

- **Unit**: Unit 4 — Jenkins Validation.
- **Stories**: US-05; cross-cutting support for US-02.
- **Requirements**: Validation-only CI behavior; compile and existing test checks; no deployment, image publication, or Git Bundle reference mutation.
- **Dependencies**: Completed Unit 1–3 code generation and reviewed target paths.
- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs`.
- **Maintained source**: `/Users/carlosdiogo/code_repo/airflow-spark-jenkins` Jenkins pipeline and validation configuration.

## Source Review Findings

- The sibling project has no maintained `Jenkinsfile`, Jenkins pipeline definition, test suite, or documented validation command. Its Jenkins Dockerfile only installs Docker CLI and configures socket group access.
- The target project likewise has no Jenkinsfile or test suite. Python source lives in DAGs, notebooks, scripts, and infrastructure helpers; shell scripts live under `scripts/` and `infra/`.
- Target Compose pins Jenkins to an immutable official image digest and grants the approved Docker socket. Jenkins has no target-specific build context or source workspace mount.
- The separate `scripts/verify-airflow-environment-dags.sh` is an operational post-start integration check. It must not be run by Jenkins because the pipeline is validation-only and may not operate Compose services.

## Purpose

Specify how Jenkins validates repository changes in the final target layout. Inspect the maintained pipeline source and existing test/compile commands, then design the smallest Jenkins validation contract that works from the target repository without deploying services or mutating Bundle refs.

## Sequential Design Steps

1. **Review current validation source**
   - Identify Jenkinsfile/pipeline files and commands in the sibling project.
   - Identify target Python sources, test suites, configuration files, and existing CI conventions without running checks.
   - Map source paths to the target repository layout and note missing or conflicting commands.
2. **Define Jenkins behavior**
   - Specify checkout, interpreter/runtime requirements, working directories, Python/shell syntax checks, existing test discovery, and result publication.
   - Define behavior for missing tools, no tests discovered, failed checks, and interrupted runs. Do not report syntax checks as test coverage.
   - Keep the job validation-only: do not deploy, build/publish platform images, change Git refs, publish bundles, or perform Docker lifecycle operations.
3. **Define CI boundaries**
   - Record the approved Jenkins Docker socket mount even though current CI does not use it.
   - Ensure validation commands do not read runtime secret files, launch the lakehouse stack, invoke Docker lifecycle commands, or modify persistent Compose volumes. The approved socket mount remains unused by CI.
   - Keep credentials out of build logs and job definitions; repository authentication, if required, is supplied by deployment configuration.
4. **Prepare review artifacts**
   - Produce the functional design, behavior rules, and command/path mapping.
   - Record unverified assumptions and defer implementation changes to Unit 4 Code Generation.

## Explicit Exclusions

- No pipeline edits or Jenkins image changes during Functional Design.
- No tests, compilation checks, builds, service startup/shutdown, secret reads, Docker socket use, image publishing, deployment, Bundle publishing, or Git ref updates.
- No new test suites; Unit 4 adapts only maintained validation checks.
- The existing Airflow DAG registration smoke check is run separately after deployment; Jenkins does not start Airflow or run that check.

## Approval Gate

Review the Unit 4 Functional Design plan before generating the design artifacts.

**Status**: Approved by the user on 2026-10-26. Functional Design artifacts approved; proceeding to Unit 4 NFR Requirements planning.
