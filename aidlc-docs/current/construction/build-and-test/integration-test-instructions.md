# Integration Test Instructions — s3-checkpoints

Against the running stack, in order:
1. `python3 infra/rustfs/bootstrap-checkpoint-keys.py` twice: the second run reports `unchanged` for every bucket.
2. `python3 scripts/verify/checkpoint-keys.py`: per key, own `checkpoints/` write, read, list, delete allowed; own other prefix, whole listing, bucket list and every other bucket refused.
3. `./scripts/lakehouse.sh rotate-checkpoint-keys --product data-products/default.yaml`: the previous secret is refused (403), the new one accepted.
4. `scripts/verify/checkpoint-stream.sh`: batch 0 in a first Spark session, resume with 0 rows in a second, checkpoint files under `s3ckpt://`, a bucket without a key refused, cleanup.
5. Airflow: trigger `default-uat-test_environment`; the run container mounts only `/run/secrets/lakehouse-checkpoints/bucket-default-uat` (read-only) and every task succeeds.
6. Jupyter (needs a developer sign-in): see e2e-test-instructions.md.
