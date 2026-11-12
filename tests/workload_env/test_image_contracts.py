"""Wiring of the shared workload environment into the images, Jenkins, and the scripts (workload-python BR-I, BR-C, BR-J).

The images themselves are built and checked live (scripts/verify/workload-python-parity.sh).
"""

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = (ROOT / "infra/spark-runtime/Dockerfile").read_text(encoding="utf-8")
JUPYTER_DIR = ROOT / "infra/jupyter/singleuser"
JUPYTER = (JUPYTER_DIR / "Dockerfile").read_text(encoding="utf-8")
VENV_PYTHON = "/opt/lakehouse/venv/bin/python"
USER_FOLDER = "~/.local/lakehouse/python3.10"


def test_both_images_install_exactly_the_lock_and_fail_the_build_otherwise():
    for dockerfile in (RUNTIME, JUPYTER):
        assert "COPY infra/workload-python/requirements.lock /opt/lakehouse/requirements.lock" in dockerfile
        assert "COPY infra/workload-python/workload_python.py /opt/lakehouse/workload_python.py" in dockerfile
        assert "--no-deps --only-binary=:all: --requirement /opt/lakehouse/requirements.lock" in dockerfile
        assert re.search(r"workload_python\.py check-venv /opt/lakehouse/venv/bin/python \\\s+--lock /opt/lakehouse/requirements.lock", dockerfile)
        assert f"PYSPARK_PYTHON={VENV_PYTHON}" in dockerfile and f"PYSPARK_DRIVER_PYTHON={VENV_PYTHON}" in dockerfile


def test_the_runtime_venv_comes_first_on_path_and_is_built_from_the_base_python():
    assert "/usr/bin/python3 -m venv /opt/lakehouse/venv" in RUNTIME and "python3.10-venv" in RUNTIME


def test_the_runtime_is_the_official_spark_image_pinned_and_run_as_root():
    """spark-base-image FR-1, FR-3."""
    assert re.search(r"FROM apache/spark:3\.5\.9-scala2\.12-java17-python3-ubuntu@sha256:[0-9a-f]{64}\n", RUNTIME)
    assert re.search(r"FROM maven:[\w.-]+@sha256:[0-9a-f]{64} AS token-provider-build", RUNTIME)
    assert "tabulario" not in RUNTIME and "\nUSER root\n" in RUNTIME
    assert "PATH=/opt/lakehouse/venv/bin:${PATH}" in RUNTIME


def test_jupyter_builds_python_310_from_conda_forge_without_writing_the_user_home():
    assert "HOME=/root mamba create" in JUPYTER and "python=3.10.16" in JUPYTER and "--channel conda-forge" in JUPYTER
    assert "/opt/lakehouse/python3.10/bin/python -m venv /opt/lakehouse/venv" in JUPYTER
    # JupyterLab keeps its own Python: the 3.10 interpreter is not put on PATH.
    path_line = next(line for line in JUPYTER.splitlines() if line.strip().startswith("PATH="))
    assert "/opt/lakehouse" not in path_line


def test_the_only_kernel_is_lakehouse_python_310_under_the_name_python3():
    kernel = json.loads((JUPYTER_DIR / "kernel.json").read_text(encoding="utf-8"))
    assert kernel["display_name"] == "Lakehouse (Python 3.10)" and kernel["argv"][0] == VENV_PYTHON
    assert kernel["argv"][-2:] == ["-f", "{connection_file}"] and "ipykernel_launcher" in kernel["argv"]
    assert kernel["env"] == {"PYSPARK_PYTHON": VENV_PYTHON, "PYSPARK_DRIVER_PYTHON": VENV_PYTHON}
    assert "COPY infra/jupyter/singleuser/kernel.json /opt/conda/share/jupyter/kernels/python3/kernel.json" in JUPYTER
    assert json.loads((JUPYTER_DIR / "lakehouse-kernels.json").read_text()) == {"KernelSpecManager": {"ensure_native_kernel": False}}
    # A config.d drop-in: the base image's jupyter_server_config.py (listen address, umask) must stay.
    assert "/etc/jupyter/jupyter_server_config.d/lakehouse-kernels.json" in JUPYTER
    assert "/etc/jupyter/jupyter_server_config.py" not in JUPYTER


def test_user_extras_folder_is_the_same_for_the_pth_file_and_the_command():
    pth = (JUPYTER_DIR / "lakehouse-user-extras.pth").read_text(encoding="utf-8")
    assert pth.startswith("import ") and len(pth.strip().splitlines()) == 1  # site runs only import lines
    assert f'expanduser("{USER_FOLDER}")' in pth and "sys.path.append" in pth  # after the venv: locked packages win
    command = JUPYTER_DIR / "lakehouse-install-requirements"
    assert os.access(command, os.X_OK)
    text = command.read_text(encoding="utf-8")
    assert '--target "$HOME/.local/lakehouse/python3.10"' in text and "--lock /opt/lakehouse/requirements.lock" in text
    # The fixed --target comes after "$@", so a user's own --target can't point the reset elsewhere.
    assert text.index('"$@"') < text.index("--target")
    assert "COPY infra/jupyter/singleuser/lakehouse-user-extras.pth /opt/lakehouse/venv/lib/python3.10/site-packages/" in JUPYTER


def test_the_lock_generator_uses_the_runtime_base_image():
    script = ROOT / "scripts/setup/lock-workload-python.sh"
    assert os.access(script, os.X_OK)
    text = script.read_text(encoding="utf-8")
    expression = re.search(r"sed -n '([^']+)'", text).group(1)
    found = subprocess.run(["sed", "-n", expression, str(ROOT / "infra/spark-runtime/Dockerfile")], capture_output=True, text=True, check=True).stdout.strip()
    assert found.startswith("apache/spark:") and "@sha256:" in found
    assert "--user root" in text and "python3.10-venv" in text
    assert f"FROM {found}" in RUNTIME
    assert "--only-binary=:all:" in text and "env -u PYTHONPATH" in text and "check-lock" in text


def test_jenkins_checks_product_extras_with_the_mounted_lock():
    compose = (ROOT / "compose.jenkins.yml").read_text(encoding="utf-8")
    assert "- ./infra/workload-python:/opt/lakehouse/workload-python:ro" in compose
    wrapper = (ROOT / "infra/jenkins/bin/lakehouse-validate-workflows").read_text(encoding="utf-8")
    assert "python3 -m lakehouse_dags.validate" in wrapper
    assert '/opt/lakehouse/workload-python/workload_python.py check-extras "$root/requirements.txt"' in wrapper
    assert "--lock /opt/lakehouse/workload-python/requirements.lock" in wrapper


def test_the_parity_verifier_compares_both_images_with_the_workspace_lock():
    script = ROOT / "scripts/verify/workload-python-parity.sh"
    assert os.access(script, os.X_OK)
    text = script.read_text(encoding="utf-8")
    assert "local/lakehouse-spark-runtime:3.5.9_1.10.2" in text and "local/lakehouse-jupyter-singleuser:6.1.1-spark" in text
    assert "check-venv" in text and 'cmp -s "$LOCK"' in text and "diff -u" in text and "Lakehouse (Python 3.10)" in text


def test_jupyter_has_git_and_the_pinned_jupyterlab_git_extension():
    """CR-4: users clone product repositories in the terminal or with the Git sidebar."""
    assert "apt-get install --yes --no-install-recommends git" in JUPYTER
    pins = (JUPYTER_DIR / "requirements.txt").read_text(encoding="utf-8").split()
    assert "jupyterlab-git==0.55.0" in pins


def test_jupyterlab_and_notebook_come_from_the_base_and_are_never_downgraded():
    """jupyter-vulnerabilities FR-2: no pin for them; the install is constrained to the base's versions."""
    lines = [l.split("#")[0].strip().lower() for l in (JUPYTER_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()]
    assert not [l for l in lines if l.split("==")[0].split(">")[0].split("<")[0] in ("jupyterlab", "notebook")]
    assert "grep -iE '^(jupyterlab|notebook)==' > /tmp/base-pins.txt" in JUPYTER and "--constraint /tmp/base-pins.txt" in JUPYTER


def test_both_images_put_the_platform_session_module_on_the_venv_path():
    """spark-session: Airflow run containers set PYTHONPATH to the bundle only, so the path comes from a .pth."""
    assert (ROOT / "infra/workload-python/lakehouse-platform.pth").read_text() == "/opt/lakehouse/python\n"
    for dockerfile in (RUNTIME, JUPYTER):
        assert "COPY infra/workload-python/python/ /opt/lakehouse/python/" in dockerfile
        assert "COPY infra/workload-python/lakehouse-platform.pth /opt/lakehouse/venv/lib/python3.10/site-packages/lakehouse-platform.pth" in dockerfile
        assert "import lakehouse_spark, lakehouse_broker_client" in dockerfile
    assert "env PYTHONPATH=/opt/lakehouse-bundle /opt/lakehouse/venv/bin/python" in RUNTIME
    pythonpath = next(line for line in JUPYTER.splitlines() if line.strip().startswith("PYTHONPATH="))
    assert "/opt/lakehouse:" not in pythonpath and "/opt/lakehouse/" not in pythonpath
    assert not (JUPYTER_DIR / "lakehouse_spark.py").exists() and not (JUPYTER_DIR / "lakehouse_broker_client.py").exists()


def test_widgets_have_matching_kernel_and_jupyterlab_versions():
    """spark-session CR-3: ipywidgets in the workload lock, jupyterlab_widgets at the same version in JupyterLab."""
    lock = (ROOT / "infra/workload-python/requirements.lock").read_text().split()
    assert "ipywidgets==8.1.9" in (ROOT / "infra/workload-python/requirements.in").read_text().split()
    lab = [line for line in (JUPYTER_DIR / "requirements.txt").read_text().split() if line.startswith("jupyterlab_widgets==")]
    assert lab and lab[0] in lock


def test_the_runtime_image_adds_pinned_s3a_jars_with_strict_checksums_and_jupyter_inherits_them():
    for artifact in ("org.apache.hadoop:hadoop-aws:3.3.4", "com.amazonaws:aws-java-sdk-bundle:1.12.262"):
        line = next(line for line in RUNTIME.splitlines() if f"-Dartifact={artifact}" in line)
        command = RUNTIME[: RUNTIME.index(line)].rsplit("mvn ", 1)[1]
        assert "--strict-checksums" in command
    assert "COPY --from=token-provider-build /build/s3a/hadoop-aws-3.3.4.jar /build/s3a/aws-java-sdk-bundle-1.12.262.jar /opt/spark/jars/" in RUNTIME
    # The Jupyter image takes /opt/spark, jars included, from the runtime image.
    assert "COPY --from=spark-runtime /opt/spark /opt/spark" in JUPYTER
