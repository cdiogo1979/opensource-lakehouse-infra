# Unit 1 Functional Design Clarification — Partial Provider Failure

The initial answers select a redacted per-provider result, preservation of successful resources, and retry after failure. The draft also specifies Kerberos-before-RustFS ordering. These leave open whether the second independent provider should still be attempted after the first fails.

## Question 1

If Kerberos or RustFS provisioning fails, should the operation still attempt the other provider?

A) Attempt both independent providers, report each as ready/failed, and return overall failure if either fails. Keep successful resources for a retry.

B) Fail fast in the order Kerberos then RustFS; after a Kerberos failure, report RustFS as not attempted. Retain successful prior resources.

C) Other (describe after `[Answer]:`)

[Answer]:A
