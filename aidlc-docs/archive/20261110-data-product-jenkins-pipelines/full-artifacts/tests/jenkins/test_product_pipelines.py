"""Per-product Jenkins folders and jobs (FR-1 to FR-5; BR-1 to BR-10; P1 to P5)."""

import dataclasses
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/products"))
import product_strategies as ps  # noqa: E402

SPEC = importlib.util.spec_from_file_location("render_jenkins", ROOT / "infra/products/render_jenkins.py")
render_jenkins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_jenkins)
dp = render_jenkins.data_products
CASC = (ROOT / "infra/jenkins/casc/jenkins.yaml").read_text(encoding="utf-8")
HOOK = (ROOT / "infra/jenkins/init.groovy.d/reconcile-data-products.groovy").read_text(encoding="utf-8")
COMPOSE = (ROOT / "compose.jenkins.yml").read_text(encoding="utf-8")
LITERAL = r"'((?:[^'\\]|\\.)*)'"


def unquote(literal: str) -> str:
    """Read a Groovy single-quoted literal body back (the escapes groovy_string writes)."""
    return re.sub(r"\\(.)", lambda m: {"n": "\n"}.get(m.group(1), m.group(1)), literal)


def script(products) -> str:
    return render_jenkins.job_dsl(products)


def parsed_items(dsl: str) -> dict[str, list[str]]:
    items: dict[str, list[str]] = {}
    for kind, path in re.findall(r"^(folder|multibranchPipelineJob)\(" + LITERAL + r"\)", dsl, re.MULTILINE):
        path = unquote(path)
        if kind == "folder":
            items[path] = []
        else:
            folder, job = path.split("/")
            items[folder].append(job)
    return items


def parsed_folder_entries(dsl: str) -> dict[str, dict[str, list[str]]]:
    entries: dict[str, dict[str, list[str]]] = {}
    folder = None
    for line in dsl.splitlines():
        if match := re.match(r"folder\(" + LITERAL + r"\)", line):
            folder = unquote(match.group(1))
            entries[folder] = {}
        elif match := re.search(r"group \{ name\(" + LITERAL + r"\); permissions\(\[(.*)\]\) \}", line):
            entries[folder][unquote(match.group(1))] = [unquote(p) for p in re.findall(LITERAL, match.group(2))]
    return entries


def default():
    return dp.load_product(ROOT / "data-products/default.yaml")


def product(name, repo=None, description=None):
    document = yaml.safe_load(dp.render_template(name))
    if repo:
        document["repo"] = repo
    built = dp.parse_product(document, f"{name}.yaml")
    return dataclasses.replace(built, description=description) if description else built


# --- Contract and examples -------------------------------------------------------------


def test_default_gets_its_folder_and_both_jobs():
    dsl = script([default()])
    assert parsed_items(dsl) == {"default": ["default_ci", "default_cd"]}
    assert "includes('main uat')" in dsl and "remote('https://github.com/cdiogo1979/opensource-lakehouse.git')" in dsl
    assert "repoOwner('cdiogo1979')" in dsl and "repository('opensource-lakehouse')" in dsl
    assert "gitHubBranchDiscovery { strategyId(2) }" in dsl
    assert "forkPullRequestDiscovery" not in dsl and "PullRequestDiscovery" not in dsl
    assert dsl.count("interval('5m')") == 1 and dsl.count("interval('30m')") == 1
    assert dsl.count("scriptPath('Jenkinsfile')") == 2 and dsl.count("discardOldItems") == 2
    assert render_jenkins.render_state([default()]) == '{\n  "default": [\n    "default_ci",\n    "default_cd"\n  ]\n}\n'


def test_owner_is_folder_admin_and_roles_get_their_folder_rights():
    assert parsed_folder_entries(script([default()]))["default"] == {
        "role-default-owner": list(dp.FOLDER_ADMIN_PERMISSIONS),
        "role-default-developer": ["Job/Read", "Job/Build", "Job/Cancel", "Job/Workspace"],
        "role-default-analyst": ["Job/Read"],
    }
    assert len(dp.FOLDER_ADMIN_PERMISSIONS) == 22 and not any(p.startswith("Overall/") for p in dp.FOLDER_ADMIN_PERMISSIONS)


def test_a_product_without_repo_gets_an_empty_folder():
    plain = product("sales")
    assert plain.repo is None
    assert parsed_items(script([plain])) == {"sales": []}
    assert render_jenkins.desired_items([plain]) == {"sales": []}


def test_a_non_github_repo_gets_only_the_ci_job(capsys, tmp_path, monkeypatch):
    gitlab = product("sales", {"url": "https://gitlab.example.com/team/sales.git", "prod_branch": "main", "uat_branch": "main"})
    dsl = script([gitlab])
    assert parsed_items(dsl) == {"sales": ["sales_ci"]}
    assert "includes('main')" in dsl  # equal branches are listed once
    monkeypatch.setattr(dp, "load_all", lambda: [default(), gitlab])
    assert render_jenkins.main(["--output", str(tmp_path / "casc.yaml"), "--jobs-output", str(tmp_path / "jobs.groovy"),
                                "--state-output", str(tmp_path / "state.json")]) == 3
    assert "sales: no sales_cd job (pull request discovery needs a github.com repository)." in capsys.readouterr().out


def test_the_renderer_writes_both_files_and_reports_the_plan(capsys, tmp_path, monkeypatch):
    sales = product("sales", {"url": "https://github.com/acme/sales", "prod_branch": "main", "uat_branch": "uat"})
    args = ["--output", str(tmp_path / "casc.yaml"), "--jobs-output", str(tmp_path / "jobs.groovy"),
            "--state-output", str(tmp_path / "state.json")]
    monkeypatch.setattr(dp, "load_all", lambda: [default(), sales])
    assert render_jenkins.main(args + ["--check"]) == 3 and not (tmp_path / "casc.yaml").exists()
    assert "Jenkins would create folder sales." in capsys.readouterr().out
    assert render_jenkins.main(args) == 3
    assert json.loads((tmp_path / "state.json").read_text()) == {"default": ["default_ci", "default_cd"], "sales": ["sales_ci", "sales_cd"]}
    assert (tmp_path / "jobs.groovy").read_text() == render_jenkins.job_dsl([default(), sales])
    assert "jobs:" not in (tmp_path / "casc.yaml").read_text()
    assert render_jenkins.main(args) == 0
    capsys.readouterr()
    monkeypatch.setattr(dp, "load_all", lambda: [default(), dataclasses.replace(sales, repo=None)])
    assert render_jenkins.main(args + ["--check"]) == 3
    out = capsys.readouterr().out
    assert "Jenkins would delete job sales/sales_ci (with build history)." in out
    assert "Jenkins would delete job sales/sales_cd (with build history)." in out
    assert render_jenkins.main(args + ["--exclude", "sales", "--check"]) == 3
    assert "Jenkins would delete folder sales (with jobs and build history)." in capsys.readouterr().out


def test_plan_lists_creations_and_deletions():
    assert render_jenkins.plan(None, {"a": ["a_ci"]}) == ["create folder a", "create job a/a_ci"]
    assert render_jenkins.plan({"a": ["a_ci", "a_cd"], "b": []}, {"a": ["a_ci"]}) == [
        "delete job a/a_cd (with build history)", "delete folder b (with jobs and build history)"]
    assert render_jenkins.plan({"a": ["a_ci"]}, {"a": ["a_ci"]}) == []


def test_expressions_in_a_description_stay_literal():
    # The DSL file is not read by CasC (no ${...} expansion), and Groovy single quotes never interpolate.
    sneaky = product("sales", description="Reads ${readFile:/run/secrets/jenkins_break_glass_password} it's \\ here")
    assert "Reads ${" not in render_jenkins.render(CASC, [sneaky])  # descriptions never reach the CasC file
    description = re.search(r"description\(" + LITERAL + r"\)", script([sneaky])).group(1)
    assert unquote(description) == sneaky.description + "\n\n" + render_jenkins.MARKER


def test_non_printable_values_are_refused():
    with pytest.raises(dp.ProductError):
        render_jenkins.groovy_string("tab\there")


def test_product_files_cannot_grant_owner_or_global_rights():
    for jenkins in ({"owner": ["Job/Read"]}, {"developer": ["Overall/Read"]}, {"analyst": ["Overall/Administer"]}):
        document = yaml.safe_load(dp.render_template("sales"))
        document["apps"]["jenkins"] = jenkins
        with pytest.raises(dp.ProductError, match="owner is always admin|Overall"):
            dp.parse_product(document, "sales.yaml")


def test_the_hook_applies_the_jobs_after_load_and_deletes_only_marked_managed_items():
    assert f"def marker = '{render_jenkins.MARKER}'" in HOOK
    assert "new File('/run/lakehouse/jenkins-products.json')" in HOOK
    assert "new File('/run/lakehouse/jenkins-jobs.groovy')" in HOOK
    assert "new DslScriptLoader(management).runScript(jobsFile.text)" in HOOK
    # A failed apply deletes nothing.
    assert "not applied; nothing deleted" in HOOK and HOOK.index("runScript") < HOOK.index(".delete()")
    assert "./.runtime/container-mounts/jenkins-jobs.groovy:/run/lakehouse/jenkins-jobs.groovy:ro" in COMPOSE
    assert "./.runtime/container-mounts/jenkins-products.json:/run/lakehouse/jenkins-products.json:ro" in COMPOSE
    assert ("./infra/jenkins/init.groovy.d/reconcile-data-products.groovy:"
            "/var/jenkins_home/init.groovy.d/reconcile-data-products.groovy:ro") in COMPOSE
    assert "Jenkins.get().getItems(Folder)" in HOOK  # top-level folders only
    assert "contains(marker)" in HOOK and "['_ci', '_cd'].collect { folder.name + it }" in HOOK
    assert HOOK.count(".delete()") == 2
    # A missing, unreadable, or empty state deletes nothing.
    guards = HOOK.split("Jenkins.get().getItems(Folder)", 1)[0]
    assert "state not readable" in guards and "desired.isEmpty()" in guards and guards.count("  return\n") == 3


def test_the_template_and_default_file_follow_the_folder_rule():
    for path in ("data-products/default.yaml", "infra/products/template.yaml"):
        text = (ROOT / path).read_text(encoding="utf-8")
        jenkins = yaml.safe_load(text.replace("{name}", "sales"))["apps"]["jenkins"]
        assert jenkins == {"developer": ["Job/Read", "Job/Build", "Job/Cancel", "Job/Workspace"], "analyst": ["Job/Read"]}


# --- Properties (PBT partial) ----------------------------------------------------------


@settings(print_blob=True, max_examples=200)
@given(text=ps.descriptions | st.text(min_size=0, max_size=60).filter(lambda t: all(c.isprintable() or c == "\n" for c in t)))
def test_p1_groovy_literals_round_trip(text):
    literal = render_jenkins.groovy_string(text)
    match = re.fullmatch(LITERAL, literal)
    assert match and unquote(match.group(1)) == text


described_sets = ps.product_sets.flatmap(lambda products: st.tuples(*(
    st.builds(lambda p, d: dataclasses.replace(p, description=d), st.just(p), ps.descriptions) for p in products
)).map(list))


@settings(print_blob=True, max_examples=60)
@given(products=described_sets)
def test_p2_each_folder_grants_only_its_own_groups_and_product_groups_are_global_readers(products):
    entries = parsed_folder_entries(script(products))
    for item in products:
        grants = entries[item.name]
        assert set(grants) <= set(item.groups.values())
        assert grants[item.groups["owner"]] == list(dp.FOLDER_ADMIN_PERMISSIONS)
        for role, permissions in item.jenkins.items():
            assert grants[item.groups[role]] == list(permissions)
    document = yaml.safe_load(render_jenkins.render(CASC, products))
    assert "jobs" not in document  # folders and jobs are applied by the init hook, after jobs load
    matrix = {e["group"]["name"]: e["group"]["permissions"] for e in document["jenkins"]["authorizationStrategy"]["projectMatrix"]["entries"]}
    assert matrix.pop("role-platform-admin") == ["Overall/Administer"]
    assert matrix.pop("jenkins-break-glass") == ["Overall/Administer"]
    assert all(permissions == ["Overall/Read"] for permissions in matrix.values())
    assert set(matrix) == {item.groups[role] for item in products for role in ("owner", *item.jenkins)}


@settings(print_blob=True, max_examples=60)
@given(products=described_sets)
def test_p3_the_rendered_jobs_equal_the_desired_state(products):
    desired = render_jenkins.desired_items(products)
    assert parsed_items(script(products)) == desired
    assert json.loads(render_jenkins.render_state(products)) == desired
    for item in products:
        github = item.repo is not None and dp.github_repository(item.repo.url) is not None
        assert desired[item.name] == ([f"{item.name}_ci"] if item.repo else []) + ([f"{item.name}_cd"] if github else [])


@settings(print_blob=True, max_examples=40)
@given(products=described_sets)
def test_p4_rendering_is_deterministic(products):
    assert render_jenkins.render(CASC, products) == render_jenkins.render(CASC, list(products))
    assert render_jenkins.job_dsl(products) == render_jenkins.job_dsl(list(products))
    assert render_jenkins.render_state(products) == render_jenkins.render_state(list(products))


@settings(print_blob=True, max_examples=200)
@given(github=ps.github_urls, other=ps.repo_urls.filter(lambda url: "//github.com/" not in url))
def test_p5_github_urls_map_to_owner_and_repository(github, other):
    owner, repository, url = github
    assert dp.github_repository(url) == (owner, repository)
    assert dp.github_repository(other) is None
