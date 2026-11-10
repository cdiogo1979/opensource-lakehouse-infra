# Unit Test Instructions — Polaris Database Path Layout

This focused infrastructure repository has no standalone unit-test suite for the Polaris bootstrap scripts. Run Python compilation and Bash syntax validation from `build-instructions.md`; then use the integration checks below to validate Polaris configuration and Spark-resolved table locations.

The Spark smoke job requires each `DESCRIBE TABLE EXTENDED` location to equal the expected `<bucket>/<catalog>/<database>/bootstrap_smoke_test` path after trimming an optional trailing slash. It also verifies each table contains exactly the expected single smoke row after bootstrap and reruns.
