# Technology Stack Decisions — Unit 4 NFR Requirements

## Decision Summary

| Area | Decision | Rationale / constraint |
|---|---|---|
| Jenkins validation | Retain the approved Jenkins service and validation-only pipeline | No deployment, platform image build/publish, or Bundle reference mutation is added. |
| Build execution | Enforce a 15-minute execution deadline per build, excluding executor queue time | Bounds syntax checks and any maintained validation suite; timeout fails the build. |
| Build concurrency | Permit one validation build at a time and queue further builds | Matches the local PoC boundary without making a host-capacity claim. |
| Build history | Retain up to 30 builds and up to 30 days, whichever limit is reached first | Bounds Jenkins validation history without touching project data or source references. |
| Source trust | Permit only protected-branch or maintainer-approved revisions from trusted contributors | The Jenkins service has the approved Docker socket mount; untrusted repository code must not execute in this context. |
| Docker control | Keep the approved Compose socket mount, but do not use it from pipeline commands | The mount remains a broad host-control interface and is not a sandbox. Changing it would revise the approved topology. |
| Test reporting | Run maintained tests if present and report empty discovery explicitly | The target currently has no maintained test suite; syntax validation is not test coverage. |
| DAG registration | Keep production/UAT DAG registration verification as a separate post-start check | It must not cause Jenkins to start or operate Airflow or Compose services. |

## Dependency and Change Policy

- Keep the approved Jenkins base/service topology and the validation runtime from Unit 4 Functional Design.
- Implement timeout, concurrency, retention, and source-trigger enforcement in Unit 4 Code Generation using Jenkins-supported mechanisms; do not add services or alter Compose topology for these requirements.
- Do not run arbitrary pull-request code in the Jenkins controller context. A future change to arbitrary PR validation requires a separately approved isolated execution boundary or a revised socket topology.
- Keep secrets out of source control, pipeline definitions, command output, and logs.
- NFR requirements define future verification targets; they do not claim the controls are implemented or verified.
- No tests or builds are run during this requirements stage.
