"""Offline checks for build isolation and version stamping."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("signed_ota_build", HERE / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildIsolation(unittest.TestCase):
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
            for version in ("v1.0.44", "v1.0.44-myshka.2", "v1.0.44-beta.0_myshka2",
                            "v1.0.44-beta.201_myshka2;echo injected", "v1.0.45-beta.201_myshka2"):
                work = Path(d) / "new"
                result = subprocess.run([sys.executable, str(HERE / "build.py"),
                    "--work-dir", str(work), "--version", version], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(work.exists())

    def test_bridge_final_and_stable_stamps(self):
        for version in ("v1.0.44-beta.201_myshka2", "v1.0.44-beta.202_myshka2",
                        "v1.0.44_myshka2"):
            self.assertIsNotNone(build.VERSION_RE.fullmatch(version))


if __name__ == "__main__":
    unittest.main()
