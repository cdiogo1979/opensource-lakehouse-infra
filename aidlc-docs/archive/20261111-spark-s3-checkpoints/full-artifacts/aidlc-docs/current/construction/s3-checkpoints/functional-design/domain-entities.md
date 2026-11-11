# Domain Entities — s3-checkpoints

| Entity | Attributes | Source of truth |
|---|---|---|
| **Product environment bucket** | `product`, `env` (`prod`, `uat`, `dev`), `bucket` | `infra/products/data_products.py` (`Product.environments[].bucket`) |
| **Checkpoint policy** | name `checkpoints-<bucket>`; document (see business-rules.md R1) | RustFS canned policy, generated |
| **Checkpoint user** | access key `ckpt-<bucket>`; status `enabled`; attached policy exactly `checkpoints-<bucket>` | RustFS user |
| **Checkpoint key** | `access_key` (= user name), `secret_key` (generated, 40 or more URL-safe characters) | `.runtime/credentials/checkpoint-keys/<bucket>` (600, folder 700) |
| **Staged key** | Same JSON as the key | `.runtime/container-mounts/checkpoint-keys/<bucket>` (644, folder 755) |
| **Mounted key** | Same JSON | `/run/secrets/lakehouse-checkpoints/<bucket>` (read-only bind) in a run container or Jupyter server |
| **Checkpoint location** | `s3ckpt://<bucket>/checkpoints/<product path>` | Product `configs/<env>.yml` `checkpoint_path` plus the job's subpath |

## Relationships
- A product environment bucket has exactly one checkpoint policy, user and key (1:1:1:1).
- A run container holds exactly one mounted key: the bucket of its run's product and environment (`prod` for `-main`, `uat` for `-uat`).
- A Jupyter server holds zero or more mounted keys: the `dev` buckets of the products where the user is owner or developer.
- A checkpoint location belongs to exactly one bucket; Spark uses the mounted key with that bucket name, or fails.

## Naming constraints
- Bucket names come from the product model (lowercase letters, digits, `-`), so `ckpt-<bucket>` and `checkpoints-<bucket>` are valid RustFS names and file names. C3 refuses any bucket name not matching `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$`.
