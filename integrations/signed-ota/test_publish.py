"""Publication must refuse altered files, accidental data and wrong targets."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import publish


class PublicationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "output"
        self.out.mkdir()
        self.openssl = os.environ.get("OPENSSL", "openssl")
        self.key = self.root / "test-key.pem"
        subprocess.run([self.openssl, "genpkey", "-algorithm", "ED25519", "-out", str(self.key)], check=True, capture_output=True)
        public = subprocess.check_output([self.openssl, "pkey", "-in", str(self.key), "-pubout", "-outform", "DER"])[-32:]
        self.pub_patch = patch.object(publish, "PUBLIC_KEY", base64.b64encode(public).decode())
        self.pub_patch.start()
        self.addCleanup(self.pub_patch.stop)
        self.version = "v1.0.44-beta.202_myshka2"
        self.manifest = {"version": self.version, "schema": 1, "distribution": "myshka-dot2", "channel": "beta",
                         "published_at": int(time.time()) - 10, "expires_at": int(time.time()) + 1000}
        for kind, name in [("binaries", "echod-arm-dot"), ("rootfs", "rootfs.tar.gz")]:
            data = kind.encode()
            (self.out / name).write_bytes(data)
            self.manifest[kind] = {"arm-dot": {"url": f"https://github.com/{publish.REPO}/releases/download/{self.version}/{name}",
                                              "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}}
        (self.out / "release-provenance.json").write_text("{}")
        (self.out / f"myshka-corresponding-sources-{self.version}.tar.gz").write_bytes(b"test sources")
        self.manifest["release_artifacts"] = {}
        for key, name in [("provenance", "release-provenance.json"),
                          ("corresponding_sources", f"myshka-corresponding-sources-{self.version}.tar.gz")]:
            file = self.out / name
            self.manifest["release_artifacts"][key] = {
                "url": f"https://github.com/{publish.REPO}/releases/download/{self.version}/{name}",
                "sha256": publish.sha(file), "size": file.stat().st_size}
        self.sign()

    def checksums(self):
        files = sorted(p for p in self.out.iterdir() if p.name != "SHA256SUMS")
        (self.out / "SHA256SUMS").write_text("".join(f"{publish.sha(p)}  {p.name}\n" for p in files))

    def sign(self):
        (self.out / "manifest.json").write_text(json.dumps(self.manifest))
        sig = subprocess.check_output([self.openssl, "pkeyutl", "-sign", "-inkey", str(self.key), "-rawin", "-in", str(self.out / "manifest.json")])
        (self.out / "manifest.json.sig").write_bytes(base64.b64encode(sig) + b"\n")
        self.checksums()

    def test_valid_local_release_has_no_network_side_effect(self):
        with patch.object(publish, "release", side_effect=AssertionError("network")):
            self.assertEqual(publish.verify(self.out)[0]["version"], self.version)

    def test_corrupt_asset_is_refused(self):
        (self.out / "echod-arm-dot").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            publish.verify(self.out)

    def test_matching_unsigned_checksums_do_not_allow_manifest_tampering(self):
        self.manifest["version"] = "v1.0.44-beta.203_myshka2"
        (self.out / "manifest.json").write_text(json.dumps(self.manifest))
        self.checksums()
        with self.assertRaises(subprocess.CalledProcessError):
            publish.verify(self.out)

    def test_accidental_private_file_is_not_published(self):
        (self.out / "private.txt").write_text("test")
        with self.assertRaises(ValueError):
            publish.verify(self.out)
        self.checksums()
        with self.assertRaises(ValueError):
            publish.verify(self.out)

    def test_matching_unsigned_checksums_do_not_allow_source_replacement(self):
        for name in ("release-provenance.json", f"myshka-corresponding-sources-{self.version}.tar.gz"):
            with self.subTest(name=name):
                original = (self.out / name).read_bytes()
                (self.out / name).write_bytes(b"changed")
                self.checksums()
                with self.assertRaises(ValueError):
                    publish.verify(self.out)
                (self.out / name).write_bytes(original)
                self.checksums()
    def test_signed_cross_channel_and_upstream_targets_are_refused(self):
        for field in ("channel", "url"):
            with self.subTest(field=field):
                if field == "channel":
                    self.manifest["channel"] = "stable"
                else:
                    self.manifest["channel"] = "beta"
                    self.manifest["rootfs"]["arm-dot"]["url"] = "https://example.com/rootfs.tar.gz"
                self.sign()
                with self.assertRaises(ValueError):
                    publish.verify(self.out)

    def test_signed_expired_release_is_refused(self):
        self.manifest["expires_at"] = int(time.time()) - 1
        self.sign()
        with self.assertRaises(ValueError):
            publish.verify(self.out)

    def test_symlink_is_refused(self):
        original = self.out / "echod-arm-dot"
        original.rename(self.root / "daemon")
        original.symlink_to(self.root / "daemon")
        with self.assertRaises(ValueError):
            publish.verify(self.out)

    def test_version_order(self):
        self.assertLess(publish.version_key("v1.0.44-beta.201_myshka2"), publish.version_key(self.version))
        self.assertLess(publish.version_key(self.version), publish.version_key("v1.0.44-beta.210_myshka2"))


if __name__ == "__main__":
    unittest.main()
