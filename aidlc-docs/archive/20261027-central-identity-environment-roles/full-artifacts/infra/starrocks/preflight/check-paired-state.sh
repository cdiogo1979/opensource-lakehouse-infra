#!/bin/sh
set -eu

fe_root=/state/fe
be_root=/state/be

has_payload() {
  root=$1
  if [ ! -d "$root" ] || [ ! -r "$root" ] || [ ! -x "$root" ]; then
    echo "StarRocks paired-state preflight failed: a state volume is unavailable or unreadable." >&2
    exit 1
  fi
  # Docker Desktop's Linux volumes may contain only the filesystem lost+found.
  entries=$(find "$root" -mindepth 1 -maxdepth 1 ! -name lost+found -print -quit) || {
    echo "StarRocks paired-state preflight failed: a state volume could not be inspected." >&2
    exit 1
  }
  [ -n "$entries" ]
}

fe_payload=false
be_payload=false
has_payload "$fe_root" && fe_payload=true
has_payload "$be_root" && be_payload=true

if [ "$fe_payload" = false ] && [ "$be_payload" = false ]; then
  echo "StarRocks paired-state preflight passed: both node volumes are empty."
  exit 0
fi

if [ "$fe_payload" = true ] && [ "$be_payload" = true ] \
  && [ -s "$fe_root/image/ROLE" ] \
  && [ -s "$fe_root/image/VERSION" ] \
  && [ -d "$be_root/data" ] \
  && find "$be_root" -mindepth 1 -maxdepth 5 -type f -name cluster_id -print -quit | grep -q .; then
  echo "StarRocks paired-state preflight passed: recognized FE and BE state markers are present."
  exit 0
fi

echo "StarRocks paired-state preflight failed: volumes are one-sided, unreadable, or unrecognized; state was left unchanged." >&2
exit 1
