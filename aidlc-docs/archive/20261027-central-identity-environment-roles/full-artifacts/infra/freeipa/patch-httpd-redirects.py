#!/usr/bin/env python3
"""Keep FreeIPA's canonical UI redirects working behind its published host port."""

import os
import re
from pathlib import Path


hostname = os.environ.get("FREEIPA_HOSTNAME", "ipa.lakehouse.local")
ui_port = os.environ.get("FREEIPA_UI_PORT", "8443")
if not ui_port.isdigit() or not 1 <= int(ui_port) <= 65535:
    raise SystemExit("FREEIPA_UI_PORT must be a valid TCP port")
config = Path("/etc/httpd/conf.d/ipa-rewrite.conf")
compat_config = Path("/etc/httpd/conf.d/ipa-port-compat.conf")

if not config.exists():
    raise SystemExit(1)

lines = config.read_text().splitlines(keepends=True)
updated = False
escaped_hostname = re.escape(hostname)
for index, line in enumerate(lines):
    if line.startswith("RewriteRule ^/$ "):
        old_targets = (f"https://{hostname}/ipa/ui", f"https://{hostname}:8443/ipa/ui", f"https://{hostname}:8444/ipa/ui")
        new_target = f"https://{hostname}:{ui_port}/ipa/ui"
        for old_target in old_targets:
            if old_target in line and old_target != new_target:
                lines[index] = line.replace(old_target, new_target, 1)
                updated = True
                break
    if "RewriteCond %{HTTP_HOST}" in line:
        old_conditions = (f"!^{hostname}$", f"!^{hostname}(:8443)?$", f"!^{hostname}(:8444)?$")
        new_condition = f"!^{hostname}(:{ui_port})?$"
        for old_condition in old_conditions:
            if old_condition in line and old_condition != new_condition:
                lines[index] = line.replace(old_condition, new_condition, 1)
                updated = True
                break
    if "RewriteCond %{SERVER_PORT}" in line and "!^443$" in line:
        lines[index] = line.replace("!^443$", f"!^(443|{ui_port})$", 1)
        updated = True
    elif "RewriteCond %{SERVER_PORT}" in line and any(
        item in line for item in ("!^(443|8443)$", "!^(443|8444)$")
    ):
        lines[index] = re.sub(r"!\^\(443\|\d+\)\$", f"!^(443|{ui_port})$", line, count=1)
        updated = True

if updated:
    config.write_text("".join(lines))

compat_contents = (
    f'RequestHeader edit Referer "^https://{escaped_hostname}:{ui_port}(/ipa(?:/.*)?)$" '
    f'"https://{hostname}$1"\n'
)
if not compat_config.exists() or compat_config.read_text() != compat_contents:
    compat_config.write_text(compat_contents)
    updated = True

patched = "".join(lines)
if (
    f"https://{hostname}:{ui_port}/ipa/ui" in patched
    and any(f"!^{hostname}(:{ui_port})?$" in line for line in lines)
    and any(f"!^(443|{ui_port})$" in line for line in lines)
    and compat_config.read_text() == compat_contents
):
    if updated:
        raise SystemExit(0)
    raise SystemExit(1)

raise SystemExit(2)
