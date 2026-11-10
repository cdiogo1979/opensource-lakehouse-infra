"""Shared Hypothesis generators for product files, repositories, and DAG IDs (PBT-07)."""

import sys
from pathlib import Path

import yaml
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/products"))

import data_products as dp  # noqa: E402

product_names = st.from_regex(r"[a-z][a-z0-9]{1,19}", fullmatch=True).filter(lambda n: n not in dp.RESERVED_NAMES)
branches = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9_-]{0,20}(/[A-Za-z0-9][A-Za-z0-9_-]{0,10})?", fullmatch=True).filter(
    lambda b: not b.endswith(".lock"))
repo_urls = st.builds(
    lambda host, owner, repo: f"https://{host}/{owner}/{repo}.git",
    st.sampled_from(["github.com", "gitlab.example.com", "git.internal.local"]),
    st.from_regex(r"[a-z0-9][a-z0-9-]{0,15}", fullmatch=True),
    st.from_regex(r"[a-z0-9][a-z0-9._-]{0,20}", fullmatch=True),
)
repos = st.builds(lambda url, prod, uat: {"url": url, "prod_branch": prod, "uat_branch": uat}, repo_urls, branches, branches)
workloads = st.from_regex(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,40}", fullmatch=True)


@st.composite
def products(draw, name=product_names):
    product_name = draw(name)
    document = yaml.safe_load(dp.render_template(product_name))
    repo = draw(st.one_of(st.none(), repos))
    if repo is not None:
        document["repo"] = repo
    return dp.parse_product(document, f"{product_name}.yaml")


product_sets = st.lists(products(), max_size=5, unique_by=lambda product: product.name)

# GitHub repository URLs in the shapes people paste (with or without .git, trailing slash).
github_owners = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", fullmatch=True)
github_repositories = st.from_regex(r"[A-Za-z0-9_-][A-Za-z0-9._-]{0,40}", fullmatch=True).filter(
    lambda r: r not in (".", "..") and not r.endswith(".git"))
github_urls = st.builds(lambda owner, repo, suffix: (owner, repo, f"https://github.com/{owner}/{repo}{suffix}"),
                        github_owners, github_repositories, st.sampled_from(["", ".git", "/", ".git/"]))
# Printable descriptions, including quotes, backslashes, ${...}, and non-ASCII text.
descriptions = st.text(st.characters(categories=("L", "N", "P", "S", "Zs")), min_size=1, max_size=200).filter(
    lambda text: text.isprintable() and text.strip() == text)
