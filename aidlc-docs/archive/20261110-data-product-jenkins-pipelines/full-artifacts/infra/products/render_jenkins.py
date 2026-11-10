#!/usr/bin/env python3
"""Render the Jenkins configuration from the data product files.

Each product gets a folder <name> whose owner group is its admin, and, with a repo
block, the multibranch jobs <name>_ci (prod and UAT branches) and <name>_cd (branches
with an open pull request, github.com only). Three outputs:

- the CasC file: the static template (infra/jenkins/casc/jenkins.yaml: platform
  admin and break-glass) plus Overall/Read for each product group;
- a Job DSL script with the folders, their permissions, and the jobs;
- the desired folders and jobs as JSON.

The init hook infra/jenkins/init.groovy.d/reconcile-data-products.groovy applies the
script and deletes the managed folders and jobs missing from the JSON at every start.
It runs after Jenkins has loaded its jobs; a Job DSL script in CasC runs earlier, and
the folders it creates would be dropped until the next restart. All outputs are
deterministic, so the caller restarts Jenkins only when one changed (BR-10).

  render_jenkins.py [--output FILE] [--jobs-output FILE] [--state-output FILE] [--check] [--exclude NAME]

--check prints what would change without writing. --exclude leaves out one product
(a removal renders before its file is deleted).

Exit codes: 0 unchanged, 3 written (changed), 2 invalid product files (the
existing outputs are left untouched), 1 other failures.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_products  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "infra" / "jenkins" / "casc" / "jenkins.yaml"
OUTPUT = ROOT / ".runtime" / "container-mounts" / "jenkins-casc.yaml"
JOBS_OUTPUT = ROOT / ".runtime" / "container-mounts" / "jenkins-jobs.groovy"
STATE_OUTPUT = ROOT / ".runtime" / "container-mounts" / "jenkins-products.json"
HEADER = "# Rendered by infra/products/render_jenkins.py from infra/jenkins/casc/jenkins.yaml\n# and the data product files. Do not edit; edit the template or a product file.\n"
# The reconcile hook deletes only top-level folders whose description holds this line.
MARKER = "Managed by the lakehouse data product files."
CI_SCAN = "5m"
CD_SCAN = "30m"


def groovy_string(text: str) -> str:
    """A single-quoted Groovy literal for text (no interpolation in single quotes)."""
    if any(not (char.isprintable() or char == "\n") for char in text):
        raise data_products.ProductError("Jenkins job values must be printable text.")
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


def job_names(product) -> list[str]:
    if product.repo is None:
        return []
    names = [f"{product.name}_ci"]
    if data_products.github_repository(product.repo.url):
        names.append(f"{product.name}_cd")
    return names


def desired_items(products: list) -> dict[str, list[str]]:
    return {product.name: job_names(product) for product in products}


def global_entries(products: list) -> list[dict]:
    """Overall/Read for every product group with Jenkins rights: the owner and the apps.jenkins roles."""
    return [
        {"group": {"name": product.groups[role], "permissions": ["Overall/Read"]}}
        for product in products
        for role in ("owner", *product.jenkins)
    ]


def folder_entries(product) -> list[tuple[str, tuple[str, ...]]]:
    return [(product.groups["owner"], data_products.FOLDER_ADMIN_PERMISSIONS)] + [
        (product.groups[role], permissions) for role, permissions in product.jenkins.items()
    ]


def _list(values) -> str:
    return "[" + ", ".join(groovy_string(value) for value in values) + "]"


def _multibranch(path: str, source: list[str], scan: str) -> list[str]:
    return [
        f"multibranchPipelineJob({groovy_string(path)}) {{",
        "  branchSources {",
        "    branchSource {",
        "      source {",
        *(f"        {line}" for line in source),
        "      }",
        "    }",
        "  }",
        f"  triggers {{ periodicFolderTrigger {{ interval({groovy_string(scan)}) }} }}",
        "  orphanedItemStrategy { discardOldItems { } }",
        "  factory { workflowBranchProjectFactory { scriptPath('Jenkinsfile') } }",
        "}",
    ]


def product_dsl(product) -> list[str]:
    name = product.name
    lines = [
        f"folder({groovy_string(name)}) {{",
        f"  description({groovy_string(product.description + chr(10) + chr(10) + MARKER)})",
        "  properties {",
        "    authorizationMatrix {",
        "      inheritanceStrategy { inheriting() }",
        "      entries {",
        *(f"        group {{ name({groovy_string(group)}); permissions({_list(permissions)}) }}" for group, permissions in folder_entries(product)),
        "      }",
        "    }",
        "  }",
        "}",
    ]
    if product.repo is None:
        return lines
    branches = " ".join(dict.fromkeys((product.repo.prod_branch, product.repo.uat_branch)))
    lines += _multibranch(f"{name}/{name}_ci", [
        "git {",
        f"  id({groovy_string(name + '_ci')})",
        f"  remote({groovy_string(product.repo.url)})",
        f"  traits {{ gitBranchDiscovery(); headWildcardFilter {{ includes({groovy_string(branches)}); excludes('') }} }}",
        "}",
    ], CI_SCAN)
    github = data_products.github_repository(product.repo.url)
    if github:
        owner, repository = github
        lines += _multibranch(f"{name}/{name}_cd", [
            "github {",
            f"  id({groovy_string(name + '_cd')})",
            f"  repoOwner({groovy_string(owner)})",
            f"  repository({groovy_string(repository)})",
            f"  repositoryUrl({groovy_string(f'https://github.com/{owner}/{repository}')})",
            "  configuredByUrl(true)",
            "  // Only branches that are the source of an open pull request; forks are not discovered.",
            "  traits { gitHubBranchDiscovery { strategyId(2) } }",
            "}",
        ], CD_SCAN)
    return lines


def job_dsl(products: list) -> str:
    lines = [
        "// Rendered by infra/products/render_jenkins.py from the data product files. Do not edit.",
        "// One folder per data product; the owner group is its admin. Applied at every start",
        "// by init.groovy.d/reconcile-data-products.groovy, which also deletes the leftovers.",
    ]
    for product in products:
        lines += product_dsl(product)
    return "\n".join(lines) + "\n"


def render(template_text: str, products: list) -> str:
    document = yaml.safe_load(template_text)
    entries = document["jenkins"]["authorizationStrategy"]["projectMatrix"]["entries"]
    static = {entry["group"]["name"] for entry in entries}
    clash = static & {entry["group"]["name"] for entry in global_entries(products)}
    if clash:
        raise data_products.ProductError(f"Product groups collide with static Jenkins entries: {', '.join(sorted(clash))}")
    entries.extend(global_entries(products))
    return HEADER + yaml.safe_dump(document, sort_keys=False, default_flow_style=False, width=1000)


def render_state(products: list) -> str:
    return json.dumps(desired_items(products), indent=2) + "\n"


def plan(previous: dict[str, list[str]] | None, desired: dict[str, list[str]]) -> list[str]:
    """What the next Jenkins start creates and the reconcile hook deletes."""
    previous = previous or {}
    lines = []
    for name, jobs in desired.items():
        if name not in previous:
            lines.append(f"create folder {name}")
        lines += [f"create job {name}/{job}" for job in jobs if job not in previous.get(name, [])]
        lines += [f"delete job {name}/{job} (with build history)" for job in previous.get(name, []) if job not in jobs]
    lines += [f"delete folder {name} (with jobs and build history)" for name in previous if name not in desired]
    return lines


def write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and not path.is_symlink() and path.read_text(encoding="utf-8") == text:
        return False
    if path.is_file() and not path.is_symlink():
        # Rewrite in place: Jenkins bind-mounts this file, and a file bind mount
        # keeps the old inode, so an atomic replace would never reach the container.
        with path.open("r+", encoding="utf-8") as stream:
            stream.write(text)
            stream.truncate()
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)
    return True


def _read_state(path: Path) -> dict[str, list[str]] | None:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def _display(path: Path) -> Path:
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--jobs-output", type=Path, default=JOBS_OUTPUT)
    parser.add_argument("--state-output", type=Path, default=STATE_OUTPUT)
    parser.add_argument("--check", action="store_true", help="report what would change, without writing")
    parser.add_argument("--exclude", help="leave out this product")
    args = parser.parse_args(argv)
    try:
        products = [p for p in data_products.load_all() if p.name != args.exclude]
        outputs = {
            args.output: render(TEMPLATE.read_text(encoding="utf-8"), products),
            args.jobs_output: job_dsl(products),
            args.state_output: render_state(products),
        }
    except data_products.ProductError as error:
        print(f"Jenkins configuration not rendered (the running Jenkins keeps its files): {error}", file=sys.stderr)
        return 2
    except (OSError, yaml.YAMLError, KeyError, TypeError) as error:
        print(f"Jenkins configuration render failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    for product in products:
        if product.repo is not None and f"{product.name}_cd" not in job_names(product):
            print(f"{product.name}: no {product.name}_cd job (pull request discovery needs a github.com repository).")
    changes = plan(_read_state(args.state_output), desired_items(products))
    if all(path.is_file() and path.read_text(encoding="utf-8") == text for path, text in outputs.items()):
        print("Jenkins configuration unchanged.")
        return 0
    prefix = "Jenkins would " if args.check else "Jenkins will "
    for line in changes or ["keep its folders and jobs; permissions or job settings change"]:
        print(prefix + line + ".")
    if args.check:
        print("Jenkins configuration would change.")
        return 3
    for path, text in outputs.items():
        write_if_changed(path, text)
    print(f"Jenkins configuration rendered to {', '.join(str(_display(path)) for path in outputs)}.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
