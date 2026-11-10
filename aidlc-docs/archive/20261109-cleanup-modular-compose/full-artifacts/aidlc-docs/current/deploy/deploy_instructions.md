# Deploy Instructions — Cleanup and Modular Compose

Target: a checkout of `opensource-lakehouse-infra-v2` running the `lakehouse-local` stack. The development machine already runs this change. All steps are manual, run from the repository root, and no reset is needed.

1. **Update `.env`**
   - **Action**: add `JUPYTER_ENABLED=true` and `JENKINS_ENABLED=true` if `.env` predates this change. Defaults are true, so this is optional.
   - **Validation**: `grep ENABLED .env`.
2. **Start through the modules**
   - **Action**: `./scripts/lakehouse.sh start`.
   - **Validation**: `./scripts/lakehouse.sh status` shows core plus the enabled modules healthy.
   - **Expected once**: Jenkins, JupyterHub, and the reconciler may be recreated on this first run (image rebuild without attestations). Volumes and data are unaffected.
3. **Product bootstrap**
   - **Action**: `./scripts/bootstrap-default-product.sh`.
   - **Validation**: it ends with `Default product bootstrap and smoke verification completed.`, including Spark smoke tables in all three environments and the StarRocks steps.
4. **Check that nothing is recreated**
   - **Action**: run `./scripts/lakehouse.sh start` again.
   - **Validation**: container IDs are unchanged (`docker ps --filter label=com.docker.compose.project=lakehouse-local --format '{{.Names}} {{.ID}}'`).
5. **Update local habits**
   - Manual Compose commands use `-f compose.core.yml -f compose.<module>.yml`.
   - Scripts live under `scripts/{setup,bootstrap,operations,clients,verify}/` (see the README "Scripts" table).

**Rollback**: restore the previous files from the intent archive. Resource names are unchanged, so the old `docker-compose.yml` works against the same containers and volumes. No data is involved.
