# Console Access Clarification Questions — rustfs-keycloak-oidc

## Finding (2026-10-30, interactive login by `joe-developer`)
OIDC login succeeded, but the RustFS console bucket list called `GetBucketPolicyStatus` on all three buckets, received AccessDenied, and retried in a tight loop (5,282 denials per bucket in about 80 s), so the UI appeared stuck. It was the only denied action. `role-default-owner` is unaffected (`s3:*`). The approved `read` / `read_write` action sets (Functional Design, AccessLevel; BR-5) do not include console metadata reads.

The four policies already exist in RustFS. The bootstrap refuses to change an existing policy (BR-10), so the fix also needs an update path.

## Question 1 — Console metadata access for read and read/write levels
Which read-only bucket and object metadata actions should `read` and `read_write` include so the console works?

A) Console read-metadata set: `s3:GetBucketPolicyStatus`, `s3:GetBucketVersioning`, `s3:GetBucketObjectLockConfiguration`, `s3:GetBucketTagging`, `s3:ListBucketVersions` (bucket), plus `s3:GetObjectTagging`, `s3:GetObjectVersion`, `s3:GetObjectRetention`, `s3:GetObjectLegalHold` (object). All are read-only, with no configuration writes (Recommended)

B) Minimal: add only `s3:GetBucketPolicyStatus` (fixes the observed loop); add more only if other console pages fail

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — Updating the four existing policies
How should the bootstrap move the existing policies to the corrected definitions?

A) Replace a policy only when it exactly equals the previous approved definition from this intent; any other existing content is still refused (same pattern as the Airflow callback correction) (Recommended)

B) Manual operator step: delete the four policies with the root identity, then rerun the bootstrap

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Finding 2 (2026-10-30, after the policy fix) — upstream console remount loop
You reported that the console "keeps asking for" `/rustfs/admin/v3/account/info`. A headless Edge run, recorded over the DevTools protocol, reproduced it for **every** OIDC session, owner (`s3:*`) included.
- The bucket-list page loops: each cycle repeats `account/info`, `accountinfo`, `ListBuckets`, and a listing of each bucket, at 17–50 cycles per second. Every request returns 200, with no errors.
- This is upstream bug **rustfs/console#271**, "Non-admin Browser page continuously remounts during permission refresh". All OIDC users are RustFS non-admins.
- The fix (rustfs/console#272) shipped in console **v0.1.38** on 2026-10-28.
- RustFS 1.0.4 (2026-10-25) embeds the console at build time, so it carries v0.1.37. No newer RustFS release exists, and there is no runtime override for the console.
- **Workaround verified:** opening a specific bucket (`/rustfs/console/browser?bucket=<name>`) does not loop. It makes one `account/info` call and one listing.

## Question 3 — How to handle the upstream console bug
A) Accept it as a documented upstream limitation. Document the bucket deep-link workaround in the README, and record a follow-up to move to the first RustFS release that bundles console v0.1.38 or later. You confirm the interactive login using a bucket view (Recommended)

B) Build a custom RustFS 1.0.4 image from source with console v0.1.38 embedded (new image build to maintain; larger scope)

C) Serve console v0.1.38 from a separate static container in front of the console port (new component; larger scope)

X) Other (please describe after [Answer]: tag below)

[Answer]: A
