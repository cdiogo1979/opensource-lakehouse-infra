# Infrastructure Design — Unit 4 Jenkins Validation

## Purpose and Scope

Provide a reproducible Jenkins validation pipeline for the target lakehouse repository. Jenkins checks out an admitted trusted revision, verifies Python and Bash syntax, runs maintained tests if discovered, and clearly reports an empty test suite. Jenkins does not deploy services, operate Compose, build/publish platform images, mutate Bundle references, use runtime lakehouse credentials, or execute the post-start production/UAT DAG-registration check.

This design preserves Unit 3's Jenkins service wiring. It specifies infrastructure only; no files, services, or images were changed and no tests were run.

## Existing Service Boundary and Change

The current `jenkins` service uses `jenkins/jenkins:lts-jdk21` pinned by digest, adds the host Docker socket group, publishes `8098:8080` on all host interfaces, persists `/var/jenkins_home` in `jenkins-home`, mounts `/var/run/docker.sock`, and joins `iceberg_net`. Preserve these exact network, port, volume, socket, and group settings.

Unit 4 adds a local image build so the approved controller runtime includes Python 3.10, Bash, and Git. Replace the Jenkins service's direct remote `image` reference with a local image tag and a build definition using `infra/jenkins/Dockerfile` and repository-root context. Keep the final Dockerfile stage based on the existing digest-pinned Jenkins LTS JDK 21 image. Provide Python 3.10 through a digest-pinned compatible official Python runtime stage; ensure the final image contains only the interpreter/runtime files and any explicitly required libraries. Ensure Bash and Git are present without adding Docker CLI or Docker-in-Docker. Verify interpreter ABI/runtime compatibility when building; do not silently change the Jenkins base if the multi-stage runtime is incompatible.

The built image runs as the existing Jenkins user. Keep Jenkins home and socket group behavior as currently wired. The image must not contain application credentials, keytabs, RustFS secrets, Airflow secrets, or Git credentials.

## Pipeline Source and Trusted Job Configuration

- Configure one Jenkins Pipeline-from-SCM job through the Jenkins UI after deployment. Its SCM URL, protected source ref, and optional SCM credentials are deployment inputs; do not invent or commit them.
- Configure the job to read its `Jenkinsfile` only from the protected branch or another maintainer-controlled trusted ref. Grant job configuration and build-trigger permissions only to Jenkins maintainers/trusted operators. Do not expose a free-form branch/ref build parameter, configure PR discovery, or configure a webhook to build arbitrary PR revisions.
- A maintainer-approved one-off revision may be admitted only by changing the job's SCM revision under maintainer control before the run; the Jenkinsfile must come from that admitted trusted revision. Restore the protected-ref configuration after the one-off run. Reject unknown/untrusted contributors and arbitrary PR revisions before repository code executes.
- Do not implement trust as a branch check inside the Jenkinsfile. Jenkins must load that Jenkinsfile before it can evaluate such a check.
- For private remotes, reference a Jenkins-managed SCM credential ID. Public remotes need no credential. Do not place tokens in the SCM URL, job XML, Jenkinsfile, command arguments, or logs.
- Keep the configured protected ref and remote outside source-controlled pipeline parameters. Record their operator-supplied values in Jenkins configuration, not in this repository.

This setup is a trusted local PoC, not a hardened multi-tenant Jenkins service. The Jenkins controller has the approved Docker socket mount. A repository pipeline or test executing on this controller could call the Docker API regardless of the intended pipeline instructions.

## Pipeline Execution and NFR Controls

The pipeline uses the built-in Jenkins executor, as specified by the approved Functional Design. Its declarative pipeline uses a top-level agent and a 15-minute pipeline timeout so Jenkins begins the timer only after assigning the executor. Configure per-job concurrency to queue further requests rather than aborting the active run. Apply job-specific history retention at 30 builds and 30 days, whichever limit is reached first. These controls do not define a queue wait target.

The pipeline validation stages are:

1. Verify required tools (`python3.10`, `bash`, and `git`) and report versions without exposing credentials.
2. Check out the SCM-provided admitted revision into the Jenkins-managed job workspace.
3. Syntax-compile maintained Python source using Python 3.10, redirecting bytecode/cache output to Jenkins workspace temporary state so the checkout remains unchanged.
4. Run `bash -n` against maintained shell scripts under `scripts/` and `infra/`. Do not execute those scripts.
5. Discover and run the maintained test suite only if present. If none are discovered, report “no tests discovered”; do not claim syntax checks as test coverage.
6. Publish a concise Jenkins result and use the configured retention policy for job history.

The job must not mount the target project directory, `.runtime`, lakehouse data volumes, Airflow Bundle checkouts, secret files, or Kerberos ticket caches into its workspace. Do not call Docker CLI/API or use the socket from any stage. Do not start, stop, inspect, or mutate Compose services. The separate `scripts/verify-airflow-environment-dags.sh` remains a post-start operator check.

## Service, Network, Storage, and Exposure

| Concern | Design |
|---|---|
| Service | Existing `jenkins`; local validation image derived from the immutable Jenkins LTS JDK 21 base |
| Network | Existing `iceberg_net` key and `iceberg-poc-net` network name; Git remote egress as required |
| Host access | Preserve all-interface `8098:8080`; no inbound agent port `50000` |
| Persistent state | Existing `jenkins-home` named volume only; no backup/restore claim |
| Workspace | Jenkins-managed job workspace; no host project/runtime/data mounts |
| Docker control | Existing approved Docker socket and `DOCKER_GID` access are retained; pipeline does not use the socket |
| Runtime secrets | No lakehouse, writer, Kerberos, Airflow, or RustFS credential mounts; SCM auth stays in Jenkins Credentials |
| Resources | No new fixed CPU/memory limits or capacity claim |

No new service, Jenkins agent, published port, network, persistent volume, proxy, or external CI component is introduced.

## Security and Residual Risk

The trusted-source policy limits which revisions execute, but it is not process isolation. Jenkins' own security guidance recommends that builds not execute on the built-in controller node. The approved Unit 4 Functional Design requires the built-in executor, while the approved Unit 3 service mounts the Docker socket into Jenkins. As a result, trusted repository code or tests executing on the controller can access a host-control interface. This design preserves those approved decisions and records the residual risk; it does not claim the setup is suitable for untrusted contributors or multi-tenant use.

Any future change to move builds onto an isolated agent and remove the controller socket requires a separate approved design/topology revision. This infrastructure design does not add that agent or alter the mount.

## Build and Test Verification Items

- Build the local Jenkins image and confirm the final stage still derives from the approved Jenkins digest; verify `python3.10`, Bash, Git, Java/Jenkins startup, runtime libraries, and non-root Jenkins UID behavior.
- Render Compose and verify only the image/build change; confirm the host port, named volume, network, socket mount, and group mapping remain unchanged and port 50000 remains unpublished.
- Configure the fixed trusted Pipeline-from-SCM job and inspect that only the approved protected ref can load its Jenkinsfile; test that arbitrary PRs and free-form revision selection are rejected before pipeline execution.
- Confirm maintainer-only job configuration/trigger controls and credential ID handling for public/private remotes; check logs for secret leakage.
- Run two builds and verify the second queues, then verify the 15-minute timer starts after executor assignment and times out as a non-success result.
- Verify 30-build and 30-day history retention without affecting Jenkins home service data beyond job-managed history, source repositories, Bundle references/checkouts, or lakehouse volumes.
- Confirm syntax checks and test discovery/reporting match the Functional Design, pipeline commands do not invoke Docker, and no project scripts are executed.
- Run the UAT/production DAG registration check only after Airflow is started and separately from the Jenkins pipeline.

## References

- [Jenkins Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/) — top-level agent allocation precedes pipeline options; timeout can exclude executor allocation, and pipeline options include `disableConcurrentBuilds` and `buildDiscarder`.
- [Jenkins Controller Isolation](https://www.jenkins.io/doc/book/security/controller-isolation/) — Jenkins recommends running builds on nodes other than the built-in controller node.
- [Jenkins Securing Builds](https://www.jenkins.io/doc/book/security/securing-builds/) — discusses risks from build scripts and pull request code, and trust/approval strategies.
