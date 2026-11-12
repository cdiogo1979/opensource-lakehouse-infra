# PR request — Upgrade OS packages in the images built here

## Problem
The Airflow, Jenkins, Airflow token broker, Polaris group reconciler and LDAP images took their base's OS packages as published, so 106 critical and high findings with a released fix stayed in them (Airflow 63, Jenkins 20, reconciler 19, broker 4).

## Solution
The Debian-based images run `apt-get upgrade` (Airflow, Jenkins and the broker, as root, before their own installs, then back to their users); the Alpine-based ones run `apk upgrade` before their pinned `apk add` (reconciler, LDAP). A test checks that every image built here upgrades its OS packages. Docs: vulnerability alerts page (a rebuild takes released OS fixes).

## Verification
664 tests passed, 3 skipped; rebuilt and scanned: fixable OS findings 0 in all five, Airflow critical 23 -> 10; live: services recreated healthy, Jenkins OIDC and role-matrix verifiers passed, a UAT DAG run succeeded.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
