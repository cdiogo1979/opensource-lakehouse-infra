# RustFS

Reference: object storage and its console. Back to the [README](../../README.md).

- **Buckets**: three per data product, created only if missing. Existing objects are kept.
- **Console sign-in**: the console at <http://127.0.0.1:9001/rustfs/console/> offers **Keycloak** sign-in. Each Keycloak group maps to a RustFS policy with the same name, kept in line with the product files. For `default`:

  | Group | `bucket-default` | `bucket-default-uat` | `bucket-default-dev` |
  |---|---|---|---|
  | `role-default-owner`, `role-platform-admin` | all actions | all actions | all actions |
  | `role-default-developer` | read | read | read and write |
  | `role-default-analyst` | read | — | — |
  | `role-default-writer` | read and write | read and write | read and write |

- **Logins and sessions**:
  - Users without one of these groups are refused.
  - Start logins on the console port 9001, not the S3 port.
  - Sessions last one hour, and logging out also ends the Keycloak session.
- **Root keys**: the keys in `.runtime/credentials/rustfs-access-key` and `rustfs-secret-key` are for recovery only. Polaris uses them server-side to issue temporary credentials.
- **Checkpoint users**: each bucket also has a user `ckpt-<bucket>` limited to its `checkpoints/` prefix (see [Streaming checkpoints](streaming-checkpoints.md)).
- **Bucket list**: see [Known limitations](limitations.md) for the console bucket-list issue.
