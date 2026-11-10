# Unit 5 NFR Requirements Questions

Please answer each question with a letter after `[Answer]:`.

## Question 1
What concurrent Jupyter session capacity should the local PoC support?

A) Up to all three configured users (`user_a`, `user_b`, and `admin`) running isolated notebook/Spark containers at the same time; no horizontal scaling target.

B) One notebook/Spark session at a time; users run the access scenarios serially.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 2
What performance objective should apply to session startup and Spark queries?

A) No numeric startup or query-latency target; best-effort local PoC behavior is sufficient when the operator can record the expected outcome.

B) Set numeric startup and query-latency targets for the fixed local PoC.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 3
What recovery expectation should apply to failed notebook containers and persistent workspaces?

A) Operator-led recovery: restart only the affected session after diagnosis, preserve its per-user work volume, and do not require automatic backup/restore.

B) Automatically restart failed sessions and provide a local backup/restore procedure for per-user work volumes.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 4
How should the JupyterHub and single-user image dependencies be managed?

A) Preserve the existing JupyterHub 5.3.0 and Spark 3.5.5/Iceberg 1.8.1 baselines; pin JupyterHub Python dependencies, including DockerSpawner, to compatible versions before implementation.

B) Preserve the existing image baselines but allow floating Python dependency versions to simplify local setup.

C) Permit upgrading the JupyterHub and/or Spark image baselines if compatibility work is needed.

X) Other (please describe after `[Answer]:` below)

[Answer]:A
