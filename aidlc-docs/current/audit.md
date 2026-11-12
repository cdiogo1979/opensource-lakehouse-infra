# Audit Archive Pointer

The complete audit history through intent `20261112-scan-stale-targets` is preserved at `aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/aidlc-docs/current/audit.md`.

## Intent Closure: 20261112-scan-stale-targets
**Archive**: `aidlc-docs/archive/20261112-scan-stale-targets`
**Summary**: `aidlc-docs/archive/20261112-scan-stale-targets/intent-summary.md`

## New Intent: 20261112-spark-image-hardening
**Timestamp**: 2026-11-12T17:00:00Z
**User Input**: "i still dont understand why do i see so many critical issues in the spark runtime image that we just fixed" / "yes"
**AI Response**: "Explained: the workflow scans upstream apache/spark 3.5.9 (48 critical, 31 fixable) and the maven stage (0), while the built image has 23 (16 linux-libc-dev, 7 jars). Opened the intent for items 1-3. Probes: linux-libc-dev underlies the base's compiler toolchain; purge --auto-remove removes 80 packages (Perl, X11, image libraries, libpython3.10, netbase; no runtime package); unused jar groups: Hive+Derby, ZooKeeper+Curator, Kubernetes, YARN, Mesos; spark-defaults has no Hive. Requirements FR-1 to FR-4 presented for approval."
**Context**: INCEPTION; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Requirements Analysis Approval
**Timestamp**: 2026-11-12T17:20:00Z
**User Input**: "approved and continue"
**AI Response**: "Recorded approval; minimal inline workflow plan (single unit, design stages skipped); started Code Generation."
**Context**: INCEPTION; APG-01.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Code Generation and Build and Test
**Timestamp**: 2026-11-12T18:10:00Z
**AI Response**: "Spark runtime: apt-mark manual netbase; purge --auto-remove linux-libc-dev (toolchain); removed /opt/spark/yarn and the Hive (except hive-storage-api, needed for ORC), Derby, ZooKeeper, Curator, Kubernetes, YARN, Mesos jars (206 jars left, 194 deb packages); build fails if linux-libc-dev or gcc return; build checks python3, java, spark-submit. Scan: list-images.py targets() = Compose external images + 8 built images (Compose build blocks and lakehouse.sh docker build lines; source = last FROM line); vulnerability-scan.py --build builds them, scans a docker save export with trivy --input (no Docker socket) and renames the export path to the image reference; workflow runs on ubuntu-24.04-arm, timeout 120 min, with --build. Tests: 663 passed, 3 skipped; parity OK; spark-submit smoke Parquet 5 / ORC 5 / Iceberg 2, in-memory catalog. Dry-run scan: Spark runtime criticals 23 -> 5 (Netty x3, Avro 1.7.7, jackson-mapper-asl: Spark-bundled); single-user 6; Airflow (now scanned as built) 23 (Debian perl, zlib, sqlite, libxml2, openssh; Authlib, certifi, uv) noted as follow-up."
**Context**: CONSTRUCTION; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Live Checks
**Timestamp**: 2026-11-12T18:35:00Z
**User Input**: "approved and continue"
**AI Response**: "checkpoint-stream.sh passed on the new runtime (first run 31 rows, resume 0 rows, fail-closed without key, cleanup). default-uat-test_environment run manual__2026-11-12T15:31:02 succeeded, all 9 tasks. Jupyter check requested from the user (new single-user image needs a server restart). PR description drafted."
**Context**: CONSTRUCTION; APG-01.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Jupyter Live Check
**Timestamp**: 2026-11-12T18:50:00Z
**User Input**: "worked fine"
**AI Response**: "Recorded the user's Jupyter check; Build and Test approved; committed on main with the PR description; push awaits approval."
**Context**: CONSTRUCTION/DEPLOY; APG-01.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## First Workflow Run Failed (built images)
**Timestamp**: 2026-11-12T19:10:00Z
**User Input**: (pasted the run log: every lakehouse-* target "FAILED (PermissionError)"; external images and the lock uploaded; closed earlier targets: airflow-3.3.2-python3.10, alpine-3.22, jenkins-lts-jdk21, jupyterhub, maven-3.9.9-eclipse-temurin-17, python-3.10-slim-bookworm, python-3.12-alpine, singleuser, spark-3.5.9-scala2.12-java17-python3-ubuntu, spark-iceberg-3.5.5_1.8.1)
**AI Response**: "Cause: the scanner rewrote Trivy's report in place to rename the export path; on Linux the Trivy container writes it as root, so the runner user can't (macOS Docker Desktop maps ownership, so local runs passed). Fix: write the renamed report to <name>.named.json and convert from it; failures now print the error and the free disk. Regression test with read-only Trivy outputs. 662 tests passed, 3 skipped. Second commit; push awaits approval."
**Context**: DEPLOY; APG-01.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Correction: test counts
**Timestamp**: 2026-11-12T19:15:00Z
**AI Response**: "The full suite before the fix had 661 passed, 3 skipped (reported earlier, and in commit 4aaaf5e's message, as 663); after the fix 662 passed, 3 skipped. State, summary and PR description corrected; the pushed commit message is left as is."
**Context**: DEPLOY; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---
