# Intent Summary: Platform DAG Factory

## Intent
Platform DAG Factory (`20261110-platform-dag-factory`)

## Objective
Move DAG-building logic out of product repositories: a product repository holds workflows/*.json, notebooks/ and configs/ (both also used by Jupyter), and a fixed stub; the platform's lakehouse_dags package builds the DAGs and supplies all task code.

## Date
2026-11-10

## Scope
Included: the lakehouse_dags package (spec, identity, factory, redact, validate), read-only mounts and PYTHONPATH for the dag-processor and scheduler, the Jenkins validator, sparse_dirs plus the checkout sync, README, tests, and the workload repository change (JSON, stub, factory and dev-bundle client removed, cli.task_args, Jenkinsfile stage, complete README, AGENTS.md) pushed to main and uat. Excluded: an enforcing bundle class (later phase), a Python DAG API for repositories, Jupyter changes, shared workload requirements (CR-2, next intent).

## Units / workstreams
dag-factory

## Major requirements
- Product repositories declare DAGs only in workflows/<name>.json (v1: name, schedule, description, tags; tasks with name, entrypoint, runs_after, args, retries, retry_delay_seconds, execution_timeout_seconds) and keep notebooks/ and configs/ for Airflow and Jupyter.
- The platform builds <bundle>-<name> DAGs with unchanged task IDs; no repository code runs in the scheduler; the config check runs in the Spark container.
- Jenkins validates workflows and the stub; the workload README is the complete guide (CR-1).

## Architecture and design decisions
- Q1 read-only mount; Q2 config check in the container; Q3 JSON only; Q4 args, retries, timeouts; Q5 args after --; Q6 product bundles only; Q7 validator in Jenkins; Q8 push after approval; Q9 PBT partial; Q10 enforcing bundle later.
- CR-1: workload README is the single guide; AIRFLOW_BUNDLES.md and the dev-bundle client removed.
- One invalid workflow file fails the whole stub import with every problem listed.

## Implementation decisions
- lakehouse_dags: spec/identity/validate standard library only; factory ported from the workload dag_factory.py; LakehouseOperator without template fields.
- validate_environment is an exec_run of the repository config_loader inside the Spark container, after create_cluster.
- sync-bundle-checkouts.py updates existing tracking_repo sparse checkouts before Airflow starts.
- cli.task_args() returns the arguments after --, and [] in Jupyter.

## Deviations
- Code Generation found that PythonOperator renders Jinja in op_kwargs, so {{ conn.* }} / {{ var.* }} in workflow args would have reached product code; fixed with LakehouseOperator.
- Build and Test found that GitDagBundle applies sparse_dirs only at the first clone; fixed with sync-bundle-checkouts.py before the push.
- A transient 'dubious ownership' failure of one task's bundle refresh in the first UAT run; not reproduced; recorded open.
- CR-2 (shared requirements for Airflow and Jupyter Spark) was deferred by the user to the next intent.

## Verification
See construction/build-and-test/build-and-test-summary.md. Host 458 passed, 3 skipped; Airflow image 49 passed; workload 36 passed, lint clean, validator OK. Live: platform side live with the old DAGs working; workload 9cbd6f8 pushed to main and uat (approved); both DAGs from the stub with unchanged IDs; UAT run 7/7 (an earlier run lost one task to a transient dubious-ownership bundle refresh, not reproduced, recorded open); Jenkins default_ci main #2 and uat #2 SUCCESS with the validation stage. Not run: production run, CI refusal on a pushed invalid branch, interactive task_args in Jupyter.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md

## Superseded decisions
- Each workload repository owns its DAG factory (data product Airflow bundles intent, fedf0bc) replaced by the platform lakehouse_dags factory and workflow JSON.
- validate_environment in the scheduler replaced by the check inside the Spark container.
- sparse_dirs dags, configs, notebooks replaced by dags, workflows, notebooks, configs.

## Archived artifacts
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/aidlc-docs/current/compaction/20261110-platform-dag-factory/manifest.json
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/airflow/lakehouse_dags/__init__.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/airflow/lakehouse_dags/spec.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/airflow/lakehouse_dags/identity.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/airflow/lakehouse_dags/factory.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/airflow/lakehouse_dags/redact.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/airflow/lakehouse_dags/validate.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/jenkins/bin/lakehouse-validate-workflows
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/compose.airflow.yml
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/compose.jenkins.yml
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/products/data_products.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/infra/airflow/validate-bundle-config.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/scripts/setup/sync-bundle-checkouts.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/scripts/verify/dag-factory-tests.sh
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/README.md
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/tests/airflow/workflow_strategies.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/tests/airflow/test_workflow_spec.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/tests/airflow/test_dag_factory.py
- aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/tests/airflow/test_bundle_checkout_sync.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261110-platform-dag-factory/full-artifacts/`
