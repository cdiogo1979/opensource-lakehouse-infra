# Requirement Clarification Questions — StarRocks LDAP Login

## C1 JupyterHub homes after the migration
Keycloak gives LDAP-imported users new internal IDs (`sub`); JupyterHub keys users and home volumes on `sub`.

A) Copy each migrated user's home volume to the volume for the new ID; keep the old volume (Recommended)
B) Fresh homes; old volumes kept for manual recovery
C) Switch JupyterHub to `preferred_username`, copying homes once
X) Other

[Answer]: A

## C2 The Keycloak `starrocks` token client and `starrocks-token.sh`
A) Remove both (Recommended)
B) Keep the client; remove only the script
X) Other

[Answer]: A
