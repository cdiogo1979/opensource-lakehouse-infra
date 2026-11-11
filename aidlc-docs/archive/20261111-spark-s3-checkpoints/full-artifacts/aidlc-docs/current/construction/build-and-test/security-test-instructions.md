# Security Test Instructions — s3-checkpoints

- Least privilege and the misuse case: `scripts/verify/checkpoint-keys.py` (other prefixes, other buckets, bucket list refused per key).
- Fail closed: `checkpoint-stream.sh` (a bucket without a mounted key is refused); `test_dag_factory.py` (missing, symlinked or bad keys fail before a run is registered); `test_checkpoint_key_mounts.py` (no uat or prod key in Jupyter; P2).
- Secrets: tests assert no secret in bootstrap output and no secret in error messages or `CheckpointKey` repr; settings names are covered by Spark redaction; key files 600 (store) and 644 inside the host-only `.runtime/container-mounts/` (700).
- Static analysis: `bandit -q` on the changed files reports nothing new.
