#!/bin/sh
# Export the RustFS OIDC client secret from its read-only mounted file, then
# hand over to the stock image entrypoint unchanged. RustFS 1.0.4 reads OIDC
# settings only from environment variables, so the secret is placed in this
# process environment rather than in Compose configuration.
set -eu

SECRET_FILE=/run/secrets/rustfs_oidc_client_secret

if [ ! -f "$SECRET_FILE" ] || [ ! -r "$SECRET_FILE" ]; then
  echo "ERROR: RustFS OIDC client secret file is unavailable." >&2
  exit 1
fi

IFS= read -r RUSTFS_IDENTITY_OPENID_CLIENT_SECRET < "$SECRET_FILE" || true
if [ -z "$RUSTFS_IDENTITY_OPENID_CLIENT_SECRET" ]; then
  echo "ERROR: RustFS OIDC client secret file is empty." >&2
  exit 1
fi
export RUSTFS_IDENTITY_OPENID_CLIENT_SECRET
unset SECRET_FILE

exec /entrypoint.sh "$@"
