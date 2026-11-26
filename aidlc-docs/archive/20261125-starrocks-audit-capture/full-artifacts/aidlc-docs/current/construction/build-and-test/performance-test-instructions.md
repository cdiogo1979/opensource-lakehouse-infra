# Performance — StarRocks Audit Capture

Not required. Observed: AuditLoader batches every ~60 s; ~780 staging rows in the first hour on the idle local stack; the first uat load (704 rows) took under 30 s per task. Watch the staging table size (7 days) and the FE memory after enabling connection events.
