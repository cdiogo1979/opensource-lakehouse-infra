-- Run each statement separately after logging in to Dremio as the named user.
-- The source must be the configured Hive source named `hive`.
-- A denial counts as Hive authorization evidence only when the effective Hive
-- username and denial component are observable. Login, source permission,
-- missing object, and RustFS credential errors are separate outcomes.

-- Expected: ALLOW as Dremio/Hive user_a (databaseA profile).
SELECT COUNT(*) FROM "hive"."databaseA"."customer";

-- Expected: DENY as Dremio/Hive user_a (databaseB is restricted).
SELECT COUNT(*) FROM "hive"."databaseB"."customer";

-- Expected: ALLOW as Dremio/Hive user_b.
SELECT COUNT(*) FROM "hive"."databaseA"."customer";

-- Expected: ALLOW as Dremio/Hive user_b.
SELECT COUNT(*) FROM "hive"."databaseB"."customer";
