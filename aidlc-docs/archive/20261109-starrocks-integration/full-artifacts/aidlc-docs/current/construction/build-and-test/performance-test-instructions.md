# Performance Test Instructions

No performance requirements were set; the NFR stages were skipped. Only resource fit was checked:

```sh
docker stats --no-stream lakehouse-local-starrocks-fe-1 lakehouse-local-starrocks-be-1
```

Observed: FE about 808 MiB of its 2 GiB limit, and BE about 445 MiB of its 4 GiB, with the whole stack running on a 16 GB VM. No load or concurrency test was run.
