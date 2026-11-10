#!/usr/bin/env python3
"""Keep FreeIPA's systemd journal ephemeral to avoid persisting installer argv."""

from pathlib import Path


init_script = Path("/usr/local/sbin/init")
text = init_script.read_text()
old = "mkdir -p /run/ipa /run/log $DATA/var/log/journal\nln -s $DATA/var/log/journal /run/log/journal"
new = "mkdir -p /run/ipa /run/log/journal\nchmod 2755 /run/log/journal"
if text.count(old) != 1:
    raise SystemExit("expected upstream journal link was not found exactly once")
init_script.write_text(text.replace(old, new))

journald_dropin = Path("/etc/systemd/journald.conf.d/90-freeipa-volatile.conf")
journald_dropin.parent.mkdir(parents=True, exist_ok=True)
journald_dropin.write_text("[Journal]\nStorage=volatile\n")
journald_dropin.chmod(0o644)
