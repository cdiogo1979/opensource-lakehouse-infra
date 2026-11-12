# Audit Archive Pointer

The complete audit history through intent `20261112-archive-manifests` is preserved at `aidlc-docs/archive/20261112-archive-manifests/full-artifacts/aidlc-docs/current/audit.md`.

## Intent Closure: 20261112-archive-manifests
**Archive**: `aidlc-docs/archive/20261112-archive-manifests`
**Summary**: `aidlc-docs/archive/20261112-archive-manifests/intent-summary.md`

## New Intent: 20261112-scan-alert-locations
**Timestamp**: 2026-11-12T11:30:00Z
**User Input**: "why is the code check looking into usr/local/bin/gosu:1" / "in code scanning , why do i see this twice" / "yes proceed with the scan imporvement"
**AI Response**: "Opened 20261112-scan-alert-locations (pre-approved). Findings: Trivy SARIF locates image results at '<repo>:1' or an in-image path with no fingerprints, so GitHub shows non-existent files and merges packages sharing a CVE (XKCP CVE-2022-37454 in 4 python3.9 packages; OpenSSH CVE-2026-60002 in 4 packages); spark-iceberg has 12023 results in one run. FR-1 to FR-4."
**Context**: INCEPTION (pre-approved); APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Construction, Build and Test, Closure
**Timestamp**: 2026-11-12T11:50:00Z
**User Input**: "yes proceed with the scan imporvement"
**AI Response**: "relocate() rewrites SARIF locations to the pinning line (or the lock line), adds per-package partialFingerprints (version excluded) and a headline; tests 652 passed, 3 skipped; dry runs: postgres 83/83, lock 5/5, spark-iceberg 12023/12023 with CVE-2022-37454 as 4 alerts at infra/spark-runtime/Dockerfile:21. Docs updated. Closing; push pending approval."
**Context**: CONSTRUCTION, BUILD AND TEST, closure; APG-01/APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---
