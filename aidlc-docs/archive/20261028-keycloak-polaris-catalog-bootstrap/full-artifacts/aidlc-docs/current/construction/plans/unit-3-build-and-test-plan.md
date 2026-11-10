# Unit 3 Build and Test Plan — RustFS Storage

## Scope

Verify bucket creation safety and RustFS 1.0.4 STS policy enforcement. The live Polaris catalog and Spark path belongs to U4.

## Checks

- [x] Compile the new Python helpers and validate Compose configuration.
- [x] Generate/stage protected Polaris S3 credentials and confirm config keys are mounted without displaying values.
- [x] Recreate only Polaris to load the STS signing config and confirm all five core services are healthy.
- [x] Verify the three approved bucket names; preserve all existing contents.
- [x] Request temporary RustFS credentials with a dev-only prefix policy; prove dev listing/write succeeds and production listing/write is denied.
- [x] Delete only the unique temporary probe object with the scoped session.
- [ ] Verify Polaris 1.8.0 creates the same scoped session through catalog credential vending; U4 owns the required catalogs and Spark job.
- [ ] Verify credential refresh and the complete four-role access matrix end-to-end; U4 owns those checks.

## Result

**U3 storage primitives pass; U3/U4 integrated completion remains open.** RustFS imposes a 900-second minimum STS lifetime. Evidence: `construction/unit-3/build-test-report.md`.
