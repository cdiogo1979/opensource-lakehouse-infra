"""The shared workload lock, the venv check, and product extras (workload-python BR-L, BR-V, BR-E, BR-R, BR-J).

``infra/workload-python/workload_python.py`` uses only the standard library, so these
tests run on the host. pip itself is never called: the tests replace the interpreter
with a fake script or the module's ``_pip`` with a recorder. Resolution against PyPI
is verified live (Build and Test).
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/workload-python"))
import workload_python as wp  # noqa: E402

LOCK_PATH = ROOT / "infra/workload-python/requirements.lock"


def lock_text(*lines):
    return "\n".join([wp.LOCK_HEADER, *lines]) + "\n"


# --- Lock (BR-L) ---------------------------------------------------------------------


def test_the_committed_lock_is_valid_and_holds_the_base_set_at_its_pins():
    lock, problems = wp.parse_lock(LOCK_PATH.read_text(encoding="utf-8"))
    assert problems == []
    base = {}
    for line in (ROOT / "infra/workload-python/requirements.in").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==")
            base[wp.normalize_name(name)] = version
    assert base and all(lock[name] == version for name, version in base.items())
    assert not wp.PLATFORM_MANAGED & set(lock)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("pandas==2.2.3\n", "requirements.lock:1: the first line must be the generator header"),
        (lock_text("pandas>=2"), "requirements.lock:2: not a name==version line"),
        (lock_text("pandas==2.2.3", "Pandas==2.2.3"), "requirements.lock:3: pandas appears twice"),
        (lock_text("PySpark==3.5.5"), "requirements.lock:2: pyspark is provided by the platform and must not be locked"),
        (lock_text("# only a comment"), "requirements.lock: the lock is empty"),
    ],
)
def test_a_malformed_lock_is_refused_with_the_line(text, message):
    assert message in wp.parse_lock(text)[1]


def test_names_are_normalized_as_in_pep_503():
    assert wp.normalize_name("Jupyter_Client") == "jupyter-client"
    assert wp.normalize_name("zope.interface") == "zope-interface"
    assert wp.normalize_name("a-_.b") == "a-b"


def test_freeze_output_is_read_with_normalized_names_and_direct_references_kept():
    assert wp.parse_freeze("PyYAML==6.0.2\n# comment\n-e git+x#egg=y\nfoo @ file:///w/foo\n") == {
        "pyyaml": "6.0.2", "foo": "@ file:///w/foo"}


# --- Venv check (BR-V) ---------------------------------------------------------------


def test_compare_names_missing_different_and_extra_packages():
    lock = {"pandas": "2.2.3", "numpy": "1.26.4"}
    assert wp.compare(lock, dict(lock)) == []
    assert wp.compare(lock, {"pandas": "2.2.2", "duckdb": "1.5.6"}) == [
        "numpy: missing (1.26.4 locked)",
        "pandas: 2.2.2 installed, 2.2.3 locked",
        "duckdb: 1.5.6 installed, not in the lock",
    ]
    assert wp.compare(lock, {**lock, "duckdb": "1.5.6"}, allow_extra=True) == []


def fake_python(tmp_path, version, freeze):
    """An interpreter stand-in: prints the version for -c, the freeze for -m pip, and records PYTHONPATH."""
    (tmp_path / "freeze.txt").write_text(freeze)
    script = tmp_path / "python"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "${{PYTHONPATH:-unset}} ${{PIP_INDEX_URL:-unset}}" >> {tmp_path}/env.txt\n'
        f'if [ "$1" = "-c" ]; then echo {version}; else cat {tmp_path}/freeze.txt; fi\n'
    )
    script.chmod(0o755)
    return str(script)


def test_check_venv_passes_only_for_python_310_holding_exactly_the_lock(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PYTHONPATH", "/opt/spark/python")
    monkeypatch.setenv("PIP_INDEX_URL", "https://mirror.invalid/simple")
    lock = tmp_path / "requirements.lock"
    lock.write_text(lock_text("pandas==2.2.3", "numpy==1.26.4"))
    python = fake_python(tmp_path, "3.10", "numpy==1.26.4\npandas==2.2.3\n")
    assert wp.main(["check-venv", python, "--lock", str(lock)]) == 0
    assert "OK: Python 3.10, 2 locked package(s)" in capsys.readouterr().out
    # BR-V2: neither /opt/spark/python (it would list pyspark) nor PIP_* settings reach pip.
    assert set((tmp_path / "env.txt").read_text().split()) == {"unset"}

    python = fake_python(tmp_path, "3.13", "numpy==1.26.4\npandas==2.2.3\npyspark==3.5.5\n")
    assert wp.main(["check-venv", python, "--lock", str(lock)]) == 1
    out = capsys.readouterr().out
    assert "Python 3.13, not 3.10" in out and "pyspark: 3.5.5 installed, not in the lock" in out


def test_check_venv_with_allow_extra_lists_the_additions(tmp_path, capsys):
    lock = tmp_path / "requirements.lock"
    lock.write_text(lock_text("pandas==2.2.3"))
    python = fake_python(tmp_path, "3.10", "duckdb==1.5.6\npandas==2.2.3\n")
    assert wp.main(["check-venv", python, "--lock", str(lock), "--allow-extra"]) == 0
    assert "Additional packages: duckdb==1.5.6" in capsys.readouterr().out


# --- Extras lines (BR-E) -------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "duckdb==1.5.6",
        "DuckDB",
        "requests[socks, security]>=2.31,<3",
        "numpy ~= 1.26.0",
        'tomli; python_version < "3.11"',
        "pandas==2.2.3  # also locked: allowed, the lock decides",
    ],
)
def test_plain_requirements_are_accepted(line):
    names, problems = wp.check_extras_lines(line + "\n")
    assert problems == [] and len(names) == 1


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("-r other.txt", "options are not allowed"),
        ("--index-url https://pypi.example/simple", "options are not allowed"),
        ("--extra-index-url=https://x", "options are not allowed"),
        ("-e .", "options are not allowed"),
        ("duckdb --hash=sha256:00", "not a plain requirement"),
        ("git+https://github.com/x/y.git", "URLs and paths are not allowed"),
        ("duckdb @ https://files.example/duckdb.whl", "URLs and paths are not allowed"),
        ("./vendor/pkg", "URLs and paths are not allowed"),
        ("/wheels/pkg.whl", "URLs and paths are not allowed"),
        ("~/pkg", "URLs and paths are not allowed"),
        ("duckdb==1.5.6 \\", "URLs and paths are not allowed"),
        ("duckdb===1.5.6", "not a plain requirement"),
        ("duck db", "not a plain requirement"),
        ("pyspark==3.5.5", "pyspark is provided by the platform"),
        ("Py4J", "py4j is provided by the platform"),
        ("setuptools>=70", "setuptools is provided by the platform"),
    ],
)
def test_options_urls_paths_and_platform_packages_are_refused(line, message):
    assert wp.check_extras_lines("# header\n\n" + line + "\n")[1] == [f"requirements.txt:3: {message}"]


def test_every_problem_is_reported_and_duplicates_are_refused():
    names, problems = wp.check_extras_lines("duckdb==1.5.6\n-e .\nDuckDB\npyspark\n")
    assert names == ["duckdb"]
    assert problems == [
        "requirements.txt:2: options are not allowed",
        "requirements.txt:3: duckdb appears twice",
        "requirements.txt:4: pyspark is provided by the platform",
    ]


def test_size_encoding_and_count_limits(tmp_path):
    big = tmp_path / "requirements.txt"
    big.write_bytes(b"# " + b"x" * wp.MAX_EXTRAS_BYTES)
    assert wp.read_extras(big)[1] == ["requirements.txt: larger than 64 KiB"]
    big.write_bytes(b"caf\xe9\n")
    assert wp.read_extras(big)[1] == ["requirements.txt: not UTF-8"]
    big.write_text("".join(f"pkg{i}\n" for i in range(wp.MAX_EXTRAS_REQUIREMENTS + 1)))
    assert wp.read_extras(big)[1] == ["requirements.txt: more than 200 requirements"]


def test_platform_tags_cover_every_glibc_the_runtime_accepts():
    args = wp.platform_args()
    tags = [args[i + 1] for i, arg in enumerate(args) if arg == "--platform"]
    assert tags[0] == "manylinux2014_aarch64"
    assert tags[1:] == [f"manylinux_2_{minor}_aarch64" for minor in range(17, 32)]
    assert args[:6] == ["--python-version", "3.10", "--implementation", "cp", "--abi", "cp310"]


# --- check-extras (BR-R3) ------------------------------------------------------------


class PipRecorder:
    """Stands in for ``_pip``: records each call and writes a dry-run report when asked."""

    def __init__(self, installs=(), status=0):
        self.calls, self.installs, self.status = [], list(installs), status

    def __call__(self, python, *args):
        self.calls.append(list(args))
        if "--report" in args:
            report = Path(args[args.index("--report") + 1])
            report.write_text(json.dumps({"install": [{"metadata": {"name": n, "version": v}} for n, v in self.installs]}))
        return self.status


@pytest.fixture
def lock_file(tmp_path):
    path = tmp_path / "requirements.lock"
    path.write_text(lock_text("requests==2.32.3", "urllib3==2.8.0"))
    return path


def test_check_extras_resolves_wheels_only_for_the_runtime_with_the_lock(tmp_path, lock_file, monkeypatch, capsys):
    extras = tmp_path / "requirements.txt"
    extras.write_text("duckdb==1.5.6\nrequests-toolbelt\n")
    pip = PipRecorder(installs=[("duckdb", "1.5.6"), ("requests-toolbelt", "1.0.0"), ("requests", "2.32.3")])
    monkeypatch.setattr(wp, "_pip", pip)
    assert wp.main(["check-extras", str(extras), "--lock", str(lock_file)]) == 0
    (call,) = pip.calls
    assert call[:4] == ["install", "--dry-run", "--ignore-installed", "--quiet"]
    assert "--only-binary=:all:" in call and call[call.index("--constraint") + 1] == str(lock_file)
    assert "manylinux_2_31_aarch64" in call and "--no-cache-dir" in call
    out = capsys.readouterr().out
    assert "OK: requirements.txt resolves against the platform lock (2 requirement(s))" in out
    assert "Would add: duckdb==1.5.6, requests-toolbelt==1.0.0" in out


def test_check_extras_fails_on_refused_lines_without_calling_pip_and_on_resolution_failure(tmp_path, lock_file, monkeypatch, capsys):
    extras = tmp_path / "requirements.txt"
    extras.write_text("--index-url https://x\n")
    pip = PipRecorder()
    monkeypatch.setattr(wp, "_pip", pip)
    assert wp.main(["check-extras", str(extras), "--lock", str(lock_file)]) == 1
    assert pip.calls == []
    extras.write_text("pytpch==0.2.0\n")
    monkeypatch.setattr(wp, "_pip", PipRecorder(status=1))
    assert wp.main(["check-extras", str(extras), "--lock", str(lock_file)]) == 1
    assert "does not resolve against the platform lock with prebuilt aarch64 wheels" in capsys.readouterr().out


# --- install-extras into a venv (BR-R5, BR-A) ----------------------------------------


def test_no_requirements_file_means_nothing_to_do_and_no_pip(tmp_path, lock_file, monkeypatch, capsys):
    pip = PipRecorder()
    monkeypatch.setattr(wp, "_pip", pip)
    assert wp.main(["install-extras", str(tmp_path / "requirements.txt"), "--lock", str(lock_file)]) == 0
    assert "No requirements.txt; nothing to install." in capsys.readouterr().out
    (tmp_path / "requirements.txt").write_text("# nothing yet\n")
    assert wp.main(["install-extras", str(tmp_path), "--lock", str(lock_file)]) == 0
    assert pip.calls == []
    (tmp_path / "requirements.txt").unlink()
    (tmp_path / "requirements.txt").mkdir()
    assert wp.main(["install-extras", str(tmp_path / "requirements.txt"), "--lock", str(lock_file)]) == 1


def test_install_into_the_venv_is_constrained_and_rechecked(tmp_path, lock_file, monkeypatch, capsys):
    extras = tmp_path / "requirements.txt"
    extras.write_text("duckdb==1.5.6\n")
    pip = PipRecorder()
    monkeypatch.setattr(wp, "_pip", pip)
    monkeypatch.setattr(wp, "check_venv", lambda python, lock, allow_extra=False: ([], {"duckdb": "1.5.6"}))
    assert wp.main(["install-extras", str(extras), "--lock", str(lock_file)]) == 0
    (call,) = pip.calls
    assert call[call.index("--constraint") + 1] == str(lock_file) and "--only-binary=:all:" in call
    assert "--target" not in call
    assert "Installed: duckdb==1.5.6" in capsys.readouterr().out
    # A locked version changed by the install fails the task (BR-A3).
    monkeypatch.setattr(wp, "check_venv", lambda python, lock, allow_extra=False: (["urllib3: 1.26.0 installed, 2.8.0 locked"], {}))
    assert wp.main(["install-extras", str(extras), "--lock", str(lock_file)]) == 1


# --- install-extras into the Jupyter user folder (BR-J) ------------------------------


def install_dist(target, name, version, files):
    info = target / f"{name}-{version}.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
    for relative in files:
        (target / relative).parent.mkdir(parents=True, exist_ok=True)
        (target / relative).write_text("x")
    (info / "RECORD").write_text("".join(f"{f},," + "\n" for f in [*files, f"{info.name}/METADATA", f"{info.name}/RECORD"]))
    return info


def test_target_install_adds_only_what_is_missing_and_replaces_changed_projects(tmp_path, lock_file, monkeypatch, capsys):
    target = tmp_path / "home/.local/lakehouse/python3.10"
    install_dist(target, "duckdb", "1.5.5", ["duckdb/__init__.py", "duckdb/core.so"])
    (target / wp.STAMP_NAME).write_text(hashlib.sha256(lock_file.read_bytes()).hexdigest() + "\n")
    extras = tmp_path / "requirements.txt"
    extras.write_text("duckdb==1.5.6\n")
    pip = PipRecorder(installs=[("duckdb", "1.5.6")])
    monkeypatch.setattr(wp, "_pip", pip)
    monkeypatch.setattr(wp, "check_venv", lambda python, lock, allow_extra=False: ([], {}))
    assert wp.main(["install-extras", str(extras), "--lock", str(lock_file), "--target", str(target)]) == 0
    dry_run, install = pip.calls
    assert "--dry-run" in dry_run and "--target" not in dry_run
    assert install[install.index("--target") + 1] == str(target)
    assert "--no-deps" in install and install[-4:-3] == ["duckdb==1.5.6"]
    assert not (target / "duckdb").exists() and not list(target.glob("duckdb-1.5.5.dist-info"))
    out = capsys.readouterr().out
    assert "Installed: duckdb==1.5.6" in out and "Restart the kernel" in out


def test_target_install_refuses_after_a_lock_change_until_reset(tmp_path, lock_file, monkeypatch, capsys):
    target = tmp_path / "python3.10"
    install_dist(target, "duckdb", "1.5.6", ["duckdb/__init__.py"])
    (target / wp.STAMP_NAME).write_text("0" * 64 + "\n")
    extras = tmp_path / "requirements.txt"
    extras.write_text("duckdb==1.5.6\n")
    pip = PipRecorder(installs=[("duckdb", "1.5.6")])
    monkeypatch.setattr(wp, "_pip", pip)
    monkeypatch.setattr(wp, "check_venv", lambda python, lock, allow_extra=False: ([], {}))
    args = ["install-extras", str(extras), "--lock", str(lock_file), "--target", str(target)]
    assert wp.main(args) == 1 and pip.calls == []
    assert "rerun with --reset" in capsys.readouterr().out
    assert wp.main([*args, "--reset"]) == 0
    assert (target / wp.STAMP_NAME).read_text().strip() == hashlib.sha256(lock_file.read_bytes()).hexdigest()
    assert not list(target.glob("duckdb-*.dist-info"))  # the reset emptied it; the fake pip installs nothing


def test_target_install_never_touches_a_folder_it_did_not_create(tmp_path, lock_file, monkeypatch, capsys):
    target = tmp_path / "somewhere"
    target.mkdir()
    (target / "notes.txt").write_text("mine")
    extras = tmp_path / "requirements.txt"
    extras.write_text("duckdb\n")
    monkeypatch.setattr(wp, "_pip", PipRecorder())
    assert wp.main(["install-extras", str(extras), "--lock", str(lock_file), "--target", str(target), "--reset"]) == 1
    assert (target / "notes.txt").read_text() == "mine"
    assert "did not install" in capsys.readouterr().out


def test_removal_by_record_stays_inside_the_folder(tmp_path):
    target = tmp_path / "target"
    outside = tmp_path / "outside.txt"
    outside.write_text("keep")
    info = install_dist(target, "evil", "1.0", ["evil/__init__.py"])
    with (info / "RECORD").open("a") as record:
        record.write("../outside.txt,,\n")
    wp.remove_from_target(target, info)
    assert outside.read_text() == "keep" and not (target / "evil").exists() and not info.exists()


def test_reset_needs_a_target():
    with pytest.raises(SystemExit) as error:
        wp.main(["install-extras", "--lock", "x", "--reset"])
    assert error.value.code == 2
