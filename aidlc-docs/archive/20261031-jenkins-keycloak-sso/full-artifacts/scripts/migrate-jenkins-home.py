#!/usr/bin/env python3
"""Copy the legacy Jenkins home into the v2 Jenkins volume exactly once.

The legacy volume is only ever mounted read-only. A non-empty v2 home is never
overwritten: a home with an origin marker is left alone, and one without a
marker stops start-up for operator review. The marker is written only after
the copy has been verified.
"""

from __future__ import annotations

import subprocess
import sys

TARGET_VOLUME = "lakehouse-local_jenkins-home"
LEGACY_VOLUME = "iceberg-poc-jenkins-home"
LEGACY_CONTAINER = "hive-dremio-rustfs-jenkins-1"
IMAGE = "local/lakehouse-jenkins:2.580.1"
MARKER = ".lakehouse-home-origin"
JENKINS_UID = "1000:1000"

# Run inside a throwaway container; compares both trees before writing the marker.
COPY_SCRIPT = f"""
set -eu
cp -a /src/. /dst/
summary() {{ cd "$1" && find . -path ./{MARKER} -prune -o -print | sort | wc -l && \
  find . -path ./{MARKER} -prune -o -type f -print0 | sort -z | xargs -0 -r sha256sum | sha256sum; }}
[ "$(summary /src)" = "$(summary /dst)" ] || {{ echo "Copied Jenkins home does not match the legacy home." >&2; exit 1; }}
chown {JENKINS_UID} /dst
printf 'migrated:{LEGACY_VOLUME} %s\\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /dst/{MARKER}
chown {JENKINS_UID} /dst/{MARKER}
"""
FRESH_SCRIPT = f"""
set -eu
chown {JENKINS_UID} /dst
printf 'fresh %s\\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /dst/{MARKER}
chown {JENKINS_UID} /dst/{MARKER}
"""
INSPECT_SCRIPT = f'ls -A /dst | wc -l; cat /dst/{MARKER} 2>/dev/null || true'


def decide(target_entries: int, marker: str, legacy_volume_exists: bool, legacy_running: bool) -> str:
    """Return the migration action for the observed state.

    Args:
        target_entries: Number of entries in the v2 home (0 when missing or empty).
        marker: Contents of the origin marker, or "" when absent.
        legacy_volume_exists: Whether the legacy home volume exists.
        legacy_running: Whether the legacy Jenkins container is running.

    Returns:
        One of "skip", "refuse-unmarked", "refuse-legacy-running", "copy", or "fresh".
    """
    if marker:
        return "skip"
    if target_entries:
        return "refuse-unmarked"
    if legacy_volume_exists:
        return "refuse-legacy-running" if legacy_running else "copy"
    return "fresh"


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


def volume_exists(name: str) -> bool:
    return docker("volume", "inspect", name, check=False).returncode == 0


def container_running(name: str) -> bool:
    result = docker("inspect", "--format", "{{.State.Running}}", name, check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def ensure_target_volume() -> None:
    if not volume_exists(TARGET_VOLUME):
        # Compose labels let `docker compose` adopt the volume as its own.
        docker("volume", "create", "--label", "com.docker.compose.project=lakehouse-local",
               "--label", "com.docker.compose.volume=jenkins-home", TARGET_VOLUME)


def run_in_target(script: str, *mounts: str) -> subprocess.CompletedProcess:
    volume_args = [arg for mount in mounts for arg in ("-v", mount)]
    return docker("run", "--rm", "--user", "0", "--entrypoint", "sh", *volume_args,
                  "-v", f"{TARGET_VOLUME}:/dst", IMAGE, "-c", script, check=False)


def inspect_target() -> tuple[int, str]:
    result = run_in_target(INSPECT_SCRIPT)
    if result.returncode != 0:
        raise RuntimeError("Could not inspect the v2 Jenkins home.")
    lines = result.stdout.splitlines()
    return int(lines[0]), (lines[1].strip() if len(lines) > 1 else "")


def main() -> int:
    ensure_target_volume()
    entries, marker = inspect_target()
    action = decide(entries, marker, volume_exists(LEGACY_VOLUME), container_running(LEGACY_CONTAINER))
    if action == "skip":
        print(f"Jenkins home already initialised ({marker}); no changes made.")
        return 0
    if action == "refuse-unmarked":
        print(f"ERROR: {TARGET_VOLUME} is not empty and has no origin marker; refusing to overwrite it. "
              "Inspect the volume before starting Jenkins.", file=sys.stderr)
        return 1
    if action == "refuse-legacy-running":
        print(f"ERROR: stop the legacy container {LEGACY_CONTAINER} before migrating its home.", file=sys.stderr)
        return 1
    if action == "copy":
        result = run_in_target(COPY_SCRIPT, f"{LEGACY_VOLUME}:/src:ro")
        if result.returncode != 0:
            print(f"ERROR: Jenkins home migration failed; {TARGET_VOLUME} was not marked. "
                  "Remove the partial volume after review and retry.", file=sys.stderr)
            return 1
        print(f"Copied {LEGACY_VOLUME} into {TARGET_VOLUME} and verified it; the legacy volume was not modified.")
        return 0
    result = run_in_target(FRESH_SCRIPT)
    if result.returncode != 0:
        print("ERROR: could not initialise an empty Jenkins home.", file=sys.stderr)
        return 1
    print(f"NOTICE: no legacy Jenkins home found; started {TARGET_VOLUME} empty. "
          "The opensource-lakehouse CI job is absent and must be restored from backup or recreated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
