# Requirements — Code scanning shows fixable findings only (20261112-scan-fixable-only)

Approved by the user ("1 and 2 and b2b intents, proceed with your recommended decisions").

## Intent
Of the 1 232 critical and high findings, 484 have no fix released (mostly Debian packages in the Airflow, Jenkins and token broker images). They can't be acted on and bury the actionable ones.

## Functional requirements
- **FR-1** The SARIF uploaded to Code scanning keeps only findings with a fixed version. Findings without one are left out at every severity; when a fix is released, the next weekly or push run reports them.
- **FR-2** Dependency snapshots (Dependabot) are unchanged: they are package inventories, and Dependabot decides its own alerts.
- **FR-3** Trivy's full JSON per target stays in the run's work folder (and in `--dry-run --out`), so unfixed findings can still be reviewed; the run log shows, per target, the uploaded and the left-out counts.
- **FR-4** Docs: the vulnerability alerts page states the rule, that alerts already open for unfixed findings close on the next run, and how to see unfixed ones.

## Non-functional requirements
- **NFR-1** No change to permissions, pinned tools or categories (alerts keep their fingerprints).
- **NFR-2** Tests: the filter keeps fixed findings and drops unfixed ones; the snapshot isn't filtered.

## Decisions (recommended, accepted)
- Applies to every severity, critical included: an unfixed critical has no action but a dismissal, and Trivy's JSON keeps it visible locally.
- Filtering in the scanner (Trivy 0.76.1 `convert` has no `--ignore-unfixed`), before relocation.
