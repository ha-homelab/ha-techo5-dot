"""Offline checks for build isolation and version stamping."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("signed_ota_build", HERE / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildIsolation(unittest.TestCase):
    def test_requested_toolchain_cannot_hide_a_different_compiler(self):
        env = {"GOTOOLCHAIN": build.GO_TOOLCHAIN}
        with patch.object(build, "run", return_value="go version go1.27.1 darwin/arm64"):
            with self.assertRaisesRegex(ValueError, "release compiler must be"):
                build.compiler_version(env)
        actual = f"go version {build.GO_TOOLCHAIN} linux/amd64"
        with patch.object(build, "run", return_value=actual):
            self.assertEqual(build.compiler_version(env), actual)

    def test_existing_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            marker = p / "keep"
            marker.write_text("existing build")
            with self.assertRaisesRegex(ValueError, "must not exist"):
                build.prepare(p)
            self.assertEqual(marker.read_text(), "existing build")

    def test_invalid_version_rejected_before_creating_work(self):
        with tempfile.TemporaryDirectory() as d:
            for version in ("v1.0.49", "v1.0.49-myshka.2", "v1.0.49-beta.0_myshka2",
                            "v1.0.49-beta.203_myshka2;echo injected", "v1.0.44-beta.202_myshka2"):
                work = Path(d) / "new"
                result = subprocess.run([sys.executable, str(HERE / "build.py"),
                    "--work-dir", str(work), "--version", version], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(work.exists())

    def test_current_beta_and_stable_stamps(self):
        for version in ("v1.0.49-beta.203_myshka2", "v1.0.49-beta.204_myshka2",
                        "v1.0.49_myshka2"):
            self.assertIsNotNone(build.VERSION_RE.fullmatch(version))


if __name__ == "__main__":
    unittest.main()
