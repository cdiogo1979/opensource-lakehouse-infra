"""Hypothesis properties of the workload lock and extras rules (workload-python P1 to P5).

Derandomized, so a failure replays with the same inputs; Hypothesis shrinks it and
prints the reproduction blob.
"""

import re
import sys
from pathlib import Path

from hypothesis import given, settings, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/workload-python"))
import workload_python as wp  # noqa: E402

SETTINGS = settings(derandomize=True, print_blob=True, max_examples=200)

ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
# Project names as published: letters and digits, with separators inside.
names = st.builds(
    lambda first, middle, last: first + middle + last,
    st.sampled_from(ALNUM),
    st.text(alphabet=ALNUM + "-_.", max_size=12),
    st.sampled_from(ALNUM),
).filter(lambda name: wp.normalize_name(name) not in wp.PLATFORM_MANAGED)
# Versions as pip freeze prints them: release numbers, optional pre/post/local parts.
versions = st.builds(
    lambda release, suffix, local: ".".join(map(str, release)) + suffix + local,
    st.lists(st.integers(0, 2030), min_size=1, max_size=4),
    st.sampled_from(["", "rc1", "a2", "b3", ".post1", ".dev4"]),
    st.sampled_from(["", "+local.7"]),
)
specifiers = st.lists(
    st.builds(lambda op, version: op + version, st.sampled_from(["==", "!=", "<=", ">=", "<", ">", "~="]), versions),
    max_size=3,
).map(",".join)
extras = st.lists(st.sampled_from(["socks", "security", "all", "s3"]), max_size=2, unique=True).map(
    lambda items: f"[{','.join(items)}]" if items else ""
)
markers = st.sampled_from(["", '; python_version < "3.11"', "; sys_platform == 'linux'"])
requirement_lines = st.builds(lambda n, e, s, m: n + e + s + m, names, extras, specifiers, markers)
comments = st.sampled_from(["", "# a comment", "   ", "#", "# -e not an option"])


def distinct_by_normalized(items):
    seen = set()
    return [item for item in items if not (wp.normalize_name(item[0]) in seen or seen.add(wp.normalize_name(item[0])))]


locks = st.lists(st.tuples(names, versions), min_size=1, max_size=20).map(distinct_by_normalized).map(dict)


@SETTINGS
@given(locks)
def test_p1_a_rendered_lock_parses_back_to_the_same_packages(packages):
    parsed, problems = wp.parse_lock(wp.render_lock(packages))
    assert problems == []
    assert parsed == {wp.normalize_name(name): version for name, version in packages.items()}


@SETTINGS
@given(names, names)
def test_p2_normalization_is_idempotent_and_equates_exactly_case_and_separator_variants(first, second):
    normalized = wp.normalize_name(first)
    assert wp.normalize_name(normalized) == normalized
    canonical = lambda name: re.sub(r"[-_.]+", "-", name).casefold()  # noqa: E731 - the PEP 503 oracle
    assert (wp.normalize_name(first) == wp.normalize_name(second)) == (canonical(first) == canonical(second))


@SETTINGS
@given(locks, locks, st.booleans())
def test_p3_compare_agrees_with_dictionary_comparison(lock_packages, other, allow_extra):
    lock = {wp.normalize_name(k): v for k, v in lock_packages.items()}
    installed = {wp.normalize_name(k): v for k, v in other.items()}
    problems = wp.compare(lock, installed, allow_extra)
    if allow_extra:
        expected_ok = all(installed.get(name) == version for name, version in lock.items())
    else:
        expected_ok = installed == lock
    assert (problems == []) == expected_ok
    for problem in problems:
        assert problem.split(":", 1)[0] in set(lock) | set(installed)


@SETTINGS
@given(st.lists(requirement_lines, min_size=1, max_size=8), st.data())
def test_p4_plain_lines_are_accepted_and_any_option_url_or_path_is_refused_at_its_line(lines, data):
    unique = list({wp.normalize_name(re.match(wp.NAME, line).group(0)): line for line in lines}.values())
    names_found, problems = wp.check_extras_lines("\n".join(unique))
    assert problems == [] and len(names_found) == len(unique)
    position = data.draw(st.integers(0, len(unique) - 1))
    spoil = data.draw(st.sampled_from([
        lambda line: "-e " + line,
        lambda line: "--index-url https://x " + line,
        lambda line: line.split(";")[0] + " @ https://files.example/x.whl",
        lambda line: "./" + line,
        lambda line: "git+https://example.invalid/" + line,
    ]))
    spoiled = list(unique)
    spoiled[position] = spoil(unique[position])
    _, problems = wp.check_extras_lines("\n".join(spoiled))
    assert [problem.split(":")[1] for problem in problems] == [str(position + 1)]


@SETTINGS
@given(st.lists(requirement_lines, min_size=1, max_size=8), st.lists(comments, max_size=8), st.data())
def test_p5_comments_and_blank_lines_never_change_the_accepted_set(lines, noise, data):
    unique = list({wp.normalize_name(re.match(wp.NAME, line).group(0)): line for line in lines}.values())
    mixed = list(unique)
    for comment in noise:
        mixed.insert(data.draw(st.integers(0, len(mixed))), comment)
    assert wp.check_extras_lines("\n".join(mixed)) == (wp.check_extras_lines("\n".join(unique))[0], [])
