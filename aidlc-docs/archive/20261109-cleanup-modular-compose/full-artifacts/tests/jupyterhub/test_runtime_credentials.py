"""Tests for protected, idempotent JupyterHub credential staging."""

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prepare_runtime", ROOT / "scripts/setup/prepare-runtime.py"
)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimeCredentialTests(unittest.TestCase):
    def test_create_once_is_private_and_does_not_replace_existing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hub-secret"
            runtime.create_once(path, "a" * 64 + "\n")
            with self.assertRaises(FileExistsError):
                runtime.create_once(path, "b" * 64 + "\n")
            self.assertEqual(path.read_text().strip(), "a" * 64)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_stage_copies_private_hub_secret_without_printing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credentials = root / "credentials"
            mounts = root / "mounts"
            credentials.mkdir(mode=0o700)
            mounts.mkdir(mode=0o700)
            source = credentials / "jupyterhub-oidc-client-secret"
            source.write_text("secret-value\n")
            source.chmod(0o600)
            old_credentials, old_mounts = runtime.CREDENTIALS, runtime.CONTAINER_MOUNTS
            runtime.CREDENTIALS, runtime.CONTAINER_MOUNTS = credentials, mounts
            try:
                runtime.stage_readonly_mount(source.name, 0o400)
            finally:
                runtime.CREDENTIALS, runtime.CONTAINER_MOUNTS = old_credentials, old_mounts
            destination = mounts / source.name
            self.assertEqual(destination.read_text(), "secret-value\n")
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o400)


if __name__ == "__main__":
    unittest.main()
