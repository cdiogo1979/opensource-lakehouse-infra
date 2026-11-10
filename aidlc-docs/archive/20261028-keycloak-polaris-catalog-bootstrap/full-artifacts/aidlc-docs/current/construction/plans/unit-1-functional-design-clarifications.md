# Unit 1 Functional Design Clarification — Legacy Volume Cleanup

## Context

The user selected deletion of old Hive/FreeIPA/KDC volumes in Question 1 of `unit-1-functional-design-plan.md`. The approved NFR-01 requires safe, non-destructive bootstrap and says the bootstrap never automatically deletes bucket data. To avoid conflating a one-time legacy reset with normal bootstrap, clarify the cleanup boundary.

## Question 5 — Scope and trigger for legacy volume cleanup

Should the cleanup cover only volumes belonging to the retired FreeIPA, Hive/metastore, and MIT KDC services, and require an explicit one-time cleanup action?

A) Yes. Identify the exact legacy volume names first, then provide/run a separate explicit cleanup action for only those retired-service volumes. Normal Compose startup and product bootstrap never remove volumes or RustFS objects. Preserve all RustFS object-store and unrelated service volumes (Recommended).

B) Delete all project volumes, including RustFS object data and deferred-service state, as part of normal bootstrap.

C) Do not delete legacy volumes; leave them detached and unused.

X) Other (describe exact volume scope and trigger).

[Answer]:A

## Resolution

The user chose a separate explicit cleanup action limited to the retired FreeIPA, Hive/metastore, and MIT KDC volumes after their exact names are identified. Normal Compose startup and product bootstrap will not delete volumes or RustFS objects. RustFS and unrelated service volumes are preserved. This defines the Functional Design boundary; it does not itself execute cleanup.

No volume deletion or runtime mutation has been performed.