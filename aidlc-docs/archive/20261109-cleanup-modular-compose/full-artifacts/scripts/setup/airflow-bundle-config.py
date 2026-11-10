#!/usr/bin/env python3
"""Render the fixed production/UAT Airflow Git Bundle configuration."""

import json
import os
from urllib.parse import urlsplit

repo_url = os.environ.get("LAKEHOUSE_BUNDLE_REPOSITORY_URL", "https://github.com/cdiogo1979/opensource-lakehouse.git")
parsed = urlsplit(repo_url)
if parsed.scheme not in {"https", "ssh"} or not parsed.netloc or parsed.username or parsed.password:
    raise SystemExit("LAKEHOUSE_BUNDLE_REPOSITORY_URL must be a credential-free HTTPS or SSH repository URL.")

base = {
    "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
    "kwargs": {
        "repo_url": repo_url,
        "git_conn_id": "lakehouse_git",
        "refresh_interval": 300,
        "sparse_dirs": ["dags", "configs", "notebooks"],
    },
}
bundles = []
for name, branch in (("lakehouse-main", "main"), ("lakehouse-uat", "uat")):
    bundle = {**base, "name": name, "kwargs": {**base["kwargs"], "tracking_ref": branch}}
    bundles.append(bundle)
print(json.dumps(bundles, separators=(",", ":")))
