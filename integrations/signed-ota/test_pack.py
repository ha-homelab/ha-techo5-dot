"""Offline tests. All signatures use an ephemeral test key, never a release key."""
import argparse
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("myshka_pack", Path(__file__).with_name("pack.py"))
pack = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pack
SPEC.loader.exec_module(pack)


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def seed(self):
        path = self.root / "test-seed"
        path.write_bytes(base64.b64encode(bytes(range(32))) + b"\n")
        path.chmod(0o600)
        der = pack.command(["openssl", "pkey", "-inform", "DER", "-pubout", "-outform", "DER"],
                           data=pack.SEED_DER + bytes(range(32)))
        return path, base64.b64encode(der[len(pack.PUBLIC_DER):]).decode()

    def raw_tar(self, members):
        path = self.root / "input.tar"
        with tarfile.open(path, "w") as t:
            for name, kind, data, link in members:
                m = tarfile.TarInfo(name)
                m.type = kind
                m.linkname = link
                m.size = len(data)
                t.addfile(m, io.BytesIO(data))
        return path

    def test_archive_rejects_path_traversal(self):
        for name in ("../escape", "/absolute", "a/../b", "a//b", "a\\b", "a/./b", "a\nline"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pack.read_archive(self.raw_tar([(name, tarfile.REGTYPE, b"", "")]))

    def test_archive_rejects_duplicate_links_devices_and_symlink_children(self):
        cases = [
            [("a", tarfile.REGTYPE, b"", ""), ("a", tarfile.REGTYPE, b"", "")],
            [("a", tarfile.LNKTYPE, b"", "target")],
            [("a", tarfile.CHRTYPE, b"", "")],
            [("a", tarfile.SYMTYPE, b"", "/etc"), ("a/file", tarfile.REGTYPE, b"x", "")],
        ]
        for members in cases:
            with self.subTest(members=members), self.assertRaises(ValueError):
                pack.read_archive(self.raw_tar(members))

    def test_archive_is_bounded(self):
        path = self.raw_tar([("a", tarfile.REGTYPE, b"1234", "")])
        with patch.object(pack, "MAX_EXPANDED", 3), self.assertRaises(ValueError):
            pack.read_archive(path)

    def test_archive_normalizes_metadata_and_preserves_symlinks(self):
        entries = {"z": pack.Entry(mode=0o755, data=b"program"),
                   "a": pack.Entry(tarfile.SYMTYPE, 0o777, link="/bin/z")}
        a, b = self.root / "a.tgz", self.root / "b.tgz"
        pack.write_archive(a, entries, 1234567890)
        pack.write_archive(b, dict(reversed(list(entries.items()))), 1234567890)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertEqual(pack.read_archive(a), entries)
        with tarfile.open(a) as t:
            self.assertEqual(t.getnames(), ["a", "z"])
            for member in t:
                self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 1234567890))

    def test_seed_rejects_broad_permissions_and_symlink(self):
        seed, _ = self.seed()
        seed.chmod(0o644)
        with self.assertRaises(ValueError):
            pack.read_seed(seed)
        seed.chmod(0o600)
        link = self.root / "seed-link"
        link.symlink_to(seed)
        with self.assertRaises(OSError):
            pack.read_seed(link)

    def test_signature_rejects_tampering_and_wrong_key(self):
        seed, public = self.seed()
        signed = pack.sign(b"manifest", seed, public)
        pack.verify_signature(b"manifest", signed, public)
        with self.assertRaises(ValueError):
            pack.verify_signature(b"manifest!", signed, public)
        with self.assertRaises(ValueError):
            pack.sign(b"manifest", seed, base64.b64encode(b"x" * 32).decode())

    def test_arm_binary_required(self):
        path = self.root / "daemon"
        for content in (b"shell script", b"\x7fELF\x02\x01\x01" + b"\0" * 64):
            path.write_bytes(content)
            with self.assertRaises(ValueError):
                pack.validate_elf(path)

    def git_repo(self, name, files):
        repo = self.root / name
        repo.mkdir()
        for path, data in files.items():
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "fixture"], check=True, capture_output=True)
        commit = pack.command(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
        return repo, commit

    def fixture(self):
        seed, public = self.seed()
        project, project_commit = self.git_repo("project", {
            "integrations/guarded-announcement/guarded-announcement.patch": b"guard patch",
            "integrations/signed-ota/native.patch": b"ota patch", "LICENSE": b"MIT test license"})
        daemon_repo, daemon_commit = self.git_repo("daemon-source", {"main.go": b"package main"})
        platform_repo, platform_commit = self.git_repo("platform", {"build.py": b"# fixture"})
        upstream = self.root / "upstream"
        upstream.mkdir()
        entries = {}
        for path in ("sbin/init", "bin/busybox.static", "usr/local/bin/echod", "usr/local/sbin/slotctl",
                     "usr/local/sbin/techo5-run", "etc/techo5/boot.sh", "etc/techo5-release"):
            pack.add_file(entries, path, b"unmodified upstream", 0o755)
        rootfs = upstream / "rootfs.tgz"
        third_party = upstream / "sources.tgz"
        pack.write_archive(rootfs, entries, 1234567890)
        pack.write_archive(third_party, {"LICENSE": pack.Entry(data=b"third party")}, 1234567890)
        root_record = dict(name=rootfs.name, **pack.asset(rootfs, "v1.0.44"))
        manifest = {"version": "v1.0.44", "rootfs": {"arm-dot": {k: root_record[k] for k in ("url", "sha256", "size")}}}
        data = pack.json_bytes(manifest)
        (upstream / "manifest.json").write_bytes(data)
        (upstream / "manifest.json.sig").write_bytes(pack.sign(data, seed, public))
        lock = {"version": "v1.0.44", "manifest_sha256": pack.sha(data), "upstream_public_key": public,
                "rootfs": root_record, "third_party_sources": dict(name=third_party.name, **pack.asset(third_party, "v1.0.44")),
                "daemon_commit": daemon_commit, "platform_commit": platform_commit}
        (self.root / "upstream-lock.json").write_bytes(pack.json_bytes(lock))
        binary = self.root / "echod"
        header = bytearray(52)
        header[:7] = b"\x7fELF\x01\x01\x01"
        header[16:20] = b"\x02\x00\x28\x00"
        binary.write_bytes(header + b"test daemon")
        version = "v1.0.44-beta.202_myshka2"
        record = {"upstream_commit": daemon_commit, "target": "linux/arm/v7", "build_tags": ["dot"],
                  "version": version, "binary_sha256": pack.digest(binary), "binary_bytes": binary.stat().st_size,
                  "release_public_key": public, "distribution": "myshka-dot2", "go_version": "test Go",
                  "patch_sha256": pack.sha(b"guard patch"), "ota_patch_sha256": pack.sha(b"ota patch")}
        record_file = self.root / "build.json"
        record_file.write_bytes(pack.json_bytes(record))
        return argparse.Namespace(upstream_dir=upstream, daemon=binary, build_record=record_file,
                                  seed_file=seed, project_repo=project, project_commit=project_commit,
                                  daemon_repo=daemon_repo, platform_repo=platform_repo, release=version,
                                  channel="beta", public_key=public, published_at=1800000000,
                                  expires_at=1800000000 + 180 * 86400, source_date_epoch=1800000000,
                                  source_extra=[third_party], out_dir=self.root / "release", openssl="openssl")

    def test_end_to_end_reproducibility_and_manifest_binding(self):
        args = self.fixture()
        with patch.object(pack, "HERE", self.root):
            first = pack.pack(args)
            output = args.out_dir
            args.out_dir = self.root / "second"
            second = pack.pack(args)
        self.assertEqual(first["rootfs_sha256"], second["rootfs_sha256"])
        for path in output.iterdir():
            self.assertEqual(path.read_bytes(), (args.out_dir / path.name).read_bytes())
        manifest_data = (output / "manifest.json").read_bytes()
        pack.verify_signature(manifest_data, (output / "manifest.json.sig").read_bytes(), args.public_key)
        manifest = json.loads(manifest_data)
        self.assertEqual(list(manifest["rootfs"]), ["arm-dot"])
        self.assertNotIn("assets", manifest)
        self.assertEqual(set(manifest["release_artifacts"]), {"provenance", "corresponding_sources"})
        for record in manifest["release_artifacts"].values():
            attachment = output / record["url"].split("/")[-1]
            self.assertEqual(pack.digest(attachment), record["sha256"])
            self.assertEqual(attachment.stat().st_size, record["size"])
        rootfs = output / manifest["rootfs"]["arm-dot"]["url"].split("/")[-1]
        self.assertEqual(pack.digest(rootfs), manifest["rootfs"]["arm-dot"]["sha256"])
        entries = pack.read_archive(rootfs)
        self.assertEqual(entries["usr/local/bin/echod"].data, args.daemon.read_bytes())
        self.assertEqual(entries["usr/local/sbin/slotctl"].data, b"unmodified upstream")
        self.assertIn("usr/share/licenses/myshka/LICENSE", entries)
        self.assertNotIn(args.seed_file.read_bytes().strip(), (output / "release-provenance.json").read_bytes())
        with patch.object(pack, "HERE", self.root), self.assertRaises(ValueError):
            pack.pack(args)  # Immutable output: never overwrite an earlier release.

    def test_changed_committed_patch_fails_before_output(self):
        args = self.fixture()
        record = json.loads(args.build_record.read_text())
        record["ota_patch_sha256"] = "0" * 64
        args.build_record.write_bytes(pack.json_bytes(record))
        with patch.object(pack, "HERE", self.root), self.assertRaises(ValueError):
            pack.pack(args)
        self.assertFalse(args.out_dir.exists())

    def test_private_source_path_is_refused(self):
        repo, commit = self.git_repo("private-project", {"private/state.json": b"secret"})
        with self.assertRaises(ValueError):
            pack.validate_project_paths(repo, commit)

    def test_non_archive_supplement_is_refused(self):
        args = self.fixture()
        args.source_extra = [args.seed_file]
        with patch.object(pack, "HERE", self.root), self.assertRaises(ValueError):
            pack.pack(args)
        self.assertFalse(args.out_dir.exists())

    def test_supplement_rejects_obvious_secrets_but_allows_public_material(self):
        # Construct only a header for the refusal test; no key is generated or stored.
        private_header = b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----"
        for name, data in (("id_ed25519", b"key"), ("seed.pem", b"seed"),
                           (".env", b"TOKEN=x"), ("harmless.txt", private_header)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pack.validate_supplement({name: pack.Entry(data=data)})
        pack.validate_supplement({"release-public-key.pem": pack.Entry(data=b"-----BEGIN PUBLIC KEY-----"),
                                  "LICENSE": pack.Entry(data=b"license permits private use")})

    def test_invalid_version_channel_and_expiry_are_refused(self):
        args = self.fixture()
        cases = [("v1.0.44-beta.202_myshka2", "stable", 180),
                 ("v1.0.44_myshka2", "beta", 180),
                 ("v1.0.44-myshka.2.beta.2", "beta", 180),
                 ("v1.0.44-beta.202_myshka2", "beta", 367),
                 ("v1.0.44-beta.202_myshka2", "beta", 0)]
        for version, channel, days in cases:
            args.release, args.channel = version, channel
            args.expires_at = args.published_at + days * 86400
            with self.subTest(version=version, channel=channel, days=days), patch.object(pack, "HERE", self.root), self.assertRaises(ValueError):
                pack.pack(args)


if __name__ == "__main__":
    unittest.main()
