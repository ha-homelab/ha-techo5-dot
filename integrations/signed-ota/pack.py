#!/usr/bin/env python3
"""Reproduce and sign a Dot 2 rootfs derivative from pinned public inputs.

No network, extraction onto the host filesystem, publication, or device access.
The signing seed is read from an existing private file and never put in outputs.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zlib

HERE = Path(__file__).resolve().parent
REPOSITORY = "ha-homelab/ha-techo5-dot"
DISTRIBUTION = "myshka-dot2"
VERSION = re.compile(r"^v[0-9]{1,9}\.[0-9]{1,9}\.[0-9]{1,9}(?:-beta\.[1-9][0-9]{0,8})?_myshka[1-9][0-9]{0,8}$")
PUBLIC_DER = bytes.fromhex("302a300506032b6570032100")
SEED_DER = bytes.fromhex("302e020100300506032b657004220420")
MAX_EXPANDED = 1024 * 1024 * 1024
MAX_ENTRIES = 30000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def command(argv, *, cwd=None, data=None):
    proc = subprocess.run(argv, cwd=cwd, input=data, capture_output=True)
    if proc.returncode:
        # No command arguments, private material, or arbitrary child output in errors.
        raise ValueError(f"{Path(argv[0]).name} failed with exit {proc.returncode}")
    return proc.stdout


def decode_key(value, length=32):
    try:
        raw = base64.b64decode(value.strip(), validate=True)
    except (ValueError, TypeError):
        raise ValueError("Invalid base64 key") from None
    if len(raw) != length:
        raise ValueError("Incorrect key length")
    return raw


def read_seed(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 128):
            raise ValueError("Signing seed must be an owned regular mode-0600 file, at most 128 bytes")
        return decode_key(os.read(fd, 129))
    finally:
        os.close(fd)


def verify_signature(data, signature, public_key, openssl="openssl"):
    public = decode_key(public_key)
    raw = decode_key(signature, 64)
    with tempfile.TemporaryDirectory(prefix="myshka-verify-") as folder:
        root = Path(folder)
        (root / "public.der").write_bytes(PUBLIC_DER + public)
        (root / "input").write_bytes(data)
        (root / "signature").write_bytes(raw)
        command([openssl, "pkeyutl", "-verify", "-rawin", "-pubin", "-keyform", "DER",
                 "-inkey", str(root / "public.der"), "-in", str(root / "input"),
                 "-sigfile", str(root / "signature")])


def sign(data, seed_path, public_key, openssl="openssl"):
    seed = read_seed(seed_path)
    with tempfile.TemporaryDirectory(prefix="myshka-sign-") as folder:
        root = Path(folder)
        key = root / "private.der"
        fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(SEED_DER + seed)
        derived = command([openssl, "pkey", "-inform", "DER", "-in", str(key), "-pubout", "-outform", "DER"])
        if derived != PUBLIC_DER + decode_key(public_key):
            raise ValueError("Signing seed does not match the declared release public key")
        (root / "input").write_bytes(data)
        raw = command([openssl, "pkeyutl", "-sign", "-rawin", "-keyform", "DER",
                       "-inkey", str(key), "-in", str(root / "input")])
    signature = base64.b64encode(raw) + b"\n"
    verify_signature(data, signature, public_key, openssl)
    return signature


@dataclass(frozen=True)
class Entry:
    kind: bytes = tarfile.REGTYPE
    mode: int = 0o644
    data: bytes = b""
    link: str = ""


def safe_name(name):
    if name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/")
    if (not name or name.startswith("/") or "\\" in name or "\0" in name
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or any(ord(ch) < 32 for ch in name)):
        raise ValueError("Unsafe archive member name")
    return name


def read_archive(path):
    entries = {}
    size = 0
    with tarfile.open(path, "r:*") as archive:
        for member in archive:
            name = safe_name(member.name)
            if name in entries:
                raise ValueError("Duplicate archive member")
            if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE, tarfile.SYMTYPE}:
                raise ValueError("Unsupported archive member type")
            if member.size < 0:
                raise ValueError("Invalid archive member size")
            size += member.size
            if size > MAX_EXPANDED or len(entries) >= MAX_ENTRIES:
                raise ValueError("Archive exceeds bounded input size")
            content = archive.extractfile(member).read() if member.isfile() else b""
            if member.isfile() and len(content) != member.size:
                raise ValueError("Truncated archive member")
            entries[name] = Entry(tarfile.REGTYPE if member.isfile() else member.type,
                                  member.mode & 0o7777, content, member.linkname)
    # No child may hide under a symlink or regular file. Absolute system symlink
    # targets are retained; this program never follows or extracts those links.
    for name in entries:
        for parent in PurePosixPath(name).parents:
            if str(parent) != "." and str(parent) in entries and entries[str(parent)].kind != tarfile.DIRTYPE:
                raise ValueError("Archive child under non-directory member")
    return entries


def add_file(entries, name, data, mode=0o644):
    name = safe_name(name)
    for parent in reversed(PurePosixPath(name).parents):
        if str(parent) == ".":
            continue
        key = str(parent)
        if key in entries and entries[key].kind != tarfile.DIRTYPE:
            raise ValueError("Output parent is not a directory")
        entries.setdefault(key, Entry(tarfile.DIRTYPE, 0o755))
    entries[name] = Entry(tarfile.REGTYPE, mode, data)


def write_archive(path, entries, epoch):
    if not 0 <= epoch <= 0xFFFFFFFF:
        raise ValueError("SOURCE_DATE_EPOCH outside gzip timestamp range")
    with Path(path).open("xb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=epoch, compresslevel=9) as gz:
            with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                for name in sorted(entries):
                    entry = entries[name]
                    info = tarfile.TarInfo(name)
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    info.mtime = epoch
                    info.type, info.mode, info.linkname = entry.kind, entry.mode, entry.link
                    info.size = len(entry.data) if entry.kind == tarfile.REGTYPE else 0
                    archive.addfile(info, io.BytesIO(entry.data) if info.size else None)


def asset(path, release):
    return {"url": f"https://github.com/{REPOSITORY}/releases/download/{release}/{Path(path).name}",
            "sha256": digest(path), "size": Path(path).stat().st_size}


def verify_locked(path, record):
    if Path(path).stat().st_size != record["size"] or digest(path) != record["sha256"]:
        raise ValueError("Input does not match its locked size and SHA-256")


def upstream_inputs(directory, lock, openssl):
    data = (directory / "manifest.json").read_bytes()
    if sha(data) != lock["manifest_sha256"]:
        raise ValueError("Upstream manifest does not match pinned release")
    verify_signature(data, (directory / "manifest.json.sig").read_bytes(), lock["upstream_public_key"], openssl)
    manifest = json.loads(data)
    if manifest["version"] != lock["version"] or manifest["rootfs"]["arm-dot"] != {
            key: lock["rootfs"][key] for key in ("url", "sha256", "size")}:
        raise ValueError("Upstream manifest identity mismatch")
    for name in ("rootfs", "third_party_sources"):
        verify_locked(directory / lock[name]["name"], lock[name])
    return read_archive(directory / lock["rootfs"]["name"])


def validate_rootfs(entries):
    for name in ("sbin/init", "bin/busybox.static", "usr/local/bin/echod", "usr/local/sbin/slotctl",
                 "usr/local/sbin/techo5-run", "etc/techo5/boot.sh", "etc/techo5-release"):
        if name not in entries or entries[name].kind != tarfile.REGTYPE:
            raise ValueError("Rootfs lacks a required regular file")
    for name, entry in entries.items():
        if entry.kind != tarfile.REGTYPE:
            continue
        if (name.startswith(("data/", "store/", "android/", "vendor/", "lib/firmware/", "root/.ssh/"))
                or re.search(r"(^|/)ssh_host_.*_key$", name)
                or name.endswith(("/phone.json", "/state.json", "/psk"))):
            raise ValueError("Rootfs contains device state, firmware, or a private key")


def git_file(repo, commit, path):
    return command(["git", "show", f"{commit}:{path}"], cwd=repo)


def git_archive(repo, commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Source commit must be an exact full SHA")
    actual = command(["git", "rev-parse", commit + "^{commit}"], cwd=repo).decode().strip()
    if actual != commit:
        raise ValueError("Source repository lacks the exact commit")
    return command(["git", "archive", "--format=tar", commit], cwd=repo)


def validate_project_paths(repo, commit):
    names = command(["git", "ls-tree", "-r", "--name-only", "-z", commit], cwd=repo).split(b"\0")
    for raw in filter(None, names):
        name = safe_name(raw.decode())
        parts = name.split("/")
        if ("private" in parts or ".ssh" in parts or parts[-1] in {".env", "id_rsa", "id_ed25519"}
                or parts[-1].endswith((".pem", ".key"))):
            raise ValueError("Project source tree contains a private path")


def validate_supplement(entries):
    """Scan the supplement wrapper, not arbitrary nested upstream test fixtures."""
    private_header = re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
    for name, entry in entries.items():
        parts = name.lower().split("/")
        leaf = parts[-1]
        if (any(part in {"private", ".ssh", ".env"} for part in parts)
                or leaf in {"id_rsa", "id_ed25519", "credentials", "credentials.json"}
                or re.search(r"(^|[-_.])(seed|secret)([-_.]|$)", leaf)
                or private_header.search(entry.data)):
            raise ValueError("Supplemental source archive contains private material")


def validate_elf(path):
    with path.open("rb") as f:
        header = f.read(52)
    # The public build must actually be an ARM ELF32 little-endian executable.
    if (len(header) < 52 or header[:7] != b"\x7fELF\x01\x01\x01"
            or int.from_bytes(header[18:20], "little") != 40
            or int.from_bytes(header[16:18], "little") not in {2, 3}):
        raise ValueError("Daemon is not an ARM ELF32 executable")


def validate_build(record, binary, release, public_key, lock, project_repo, project_commit):
    validate_elf(binary)
    expected = {"upstream_commit": lock["daemon_commit"], "target": "linux/arm/v7", "build_tags": ["dot"],
                "version": release, "binary_sha256": digest(binary), "binary_bytes": binary.stat().st_size,
                "release_public_key": public_key, "distribution": DISTRIBUTION}
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("Daemon build record does not match release inputs")
    for field, filename in (("patch_sha256", "integrations/guarded-announcement/guarded-announcement.patch"),
                            ("ota_patch_sha256", "integrations/signed-ota/native.patch")):
        if record.get(field) != sha(git_file(project_repo, project_commit, filename)):
            raise ValueError("Committed source patch differs from daemon build record")
    if "BEGIN PRIVATE KEY" in git_file(project_repo, project_commit, "integrations/signed-ota/native.patch").decode():
        raise ValueError("Private key material in source patch")
    return {key: record[key] for key in (*expected, "patch_sha256", "ota_patch_sha256", "go_version")}


def pack(args):
    lock = json.loads((HERE / "upstream-lock.json").read_text())
    match = VERSION.fullmatch(args.release)
    if not match or ("beta" if "-beta." in args.release else "stable") != args.channel:
        raise ValueError("Release version and channel must agree")
    if args.published_at <= 0 or not 0 < args.expires_at - args.published_at <= 366 * 86400:
        raise ValueError("Manifest validity must be positive and at most 366 days")
    decode_key(args.public_key)
    if not command([args.openssl, "version"]).startswith(b"OpenSSL 3."):
        raise ValueError("OpenSSL 3 is required")
    if args.out_dir.exists():
        raise ValueError("Output directory must not exist; published releases are immutable")
    if not args.source_extra:
        raise ValueError("At least one audited supplemental source archive is required")
    entries = upstream_inputs(args.upstream_dir, lock, args.openssl)
    validate_rootfs(entries)
    build = validate_build(json.loads(args.build_record.read_text()), args.daemon, args.release,
                           args.public_key, lock, args.project_repo, args.project_commit)
    validate_project_paths(args.project_repo, args.project_commit)
    source_data = {
        "myshka-project.tar": git_archive(args.project_repo, args.project_commit),
        "upstream-daemon.tar": git_archive(args.daemon_repo, lock["daemon_commit"]),
        "upstream-platform.tar": git_archive(args.platform_repo, lock["platform_commit"]),
        lock["third_party_sources"]["name"]: (args.upstream_dir / lock["third_party_sources"]["name"]).read_bytes(),
    }
    for index, path in enumerate(args.source_extra, 1):
        if not path.is_file() or not tarfile.is_tarfile(path):
            raise ValueError("Supplemental source input must be a tar archive")
        # Validate members without extracting or executing any source. This also
        # prevents accidentally including a seed/key file as a supplement.
        validate_supplement(read_archive(path))
        source_data[f"supplement-{index}-{safe_name(path.name)}"] = path.read_bytes()
    sources = {name: {"sha256": sha(data), "size": len(data)} for name, data in source_data.items()}
    provenance = {"schema": 1, "distribution": DISTRIBUTION, "version": args.release,
                  "project_commit": args.project_commit, "upstream_lock": lock,
                  "daemon_build": build, "source_date_epoch": args.source_date_epoch,
                  "toolchain": {"python": platform.python_version(), "zlib": zlib.ZLIB_RUNTIME_VERSION},
                  "source_archives": sources,
                  "rootfs_changed_paths": ["etc/techo5-release", "usr/local/bin/echod", "usr/share/myshka/provenance.json", "usr/share/licenses/myshka/LICENSE"],
                  "contains_device_state": False, "contains_factory_firmware": False}
    add_file(entries, "usr/local/bin/echod", args.daemon.read_bytes(), 0o755)
    add_file(entries, "etc/techo5-release", f"myshka-dot2 {args.release} ({args.project_commit[:12]})\n".encode())
    add_file(entries, "usr/share/myshka/provenance.json", json_bytes(provenance))
    add_file(entries, "usr/share/licenses/myshka/LICENSE", git_file(args.project_repo, args.project_commit, "LICENSE"))
    validate_rootfs(entries)
    args.out_dir.parent.mkdir(parents=True, exist_ok=True)
    # Stage a complete release in a sibling directory; only a fully verified
    # signature and complete source bundle are moved into the requested output.
    with tempfile.TemporaryDirectory(prefix=".myshka-package-", dir=args.out_dir.parent) as folder:
        output = Path(folder) / "release"
        output.mkdir()
        binary = output / "echod-arm-dot"
        shutil.copyfile(args.daemon, binary)
        rootfs = output / f"myshka-dot2-rootfs-{args.release}.tar.gz"
        write_archive(rootfs, entries, args.source_date_epoch)
        source_entries = {name: Entry(data=data) for name, data in source_data.items()}
        source_entries["provenance.json"] = Entry(data=json_bytes(provenance))
        source_entries["README.txt"] = Entry(data=(
            "Myshka Dot 2 corresponding-source bundle\n\n"
            "myshka-project.tar contains the committed build, packaging instructions and patches.\n"
            "Apply its guarded-announcement.patch and signed-ota/native.patch to upstream-daemon.tar.\n"
            "upstream-platform.tar contains the exact upstream rootfs recipes and package lists.\n"
            "techo5-third-party-sources.tar.gz contains upstream's separately published component sources.\n"
            "supplement-* contains the maintainer-audited additional sources (including Alpine packages).\n"
            "Every component retains its own license. See provenance.json and each archive's inventory.\n"
            "This release does not distribute factory firmware or a kernel. Per-device files stay on the device.\n"
        ).encode())
        source_archive = output / f"myshka-corresponding-sources-{args.release}.tar.gz"
        write_archive(source_archive, source_entries, args.source_date_epoch)
        provenance_file = output / "release-provenance.json"
        provenance_file.write_bytes(json_bytes(provenance))
        manifest = {"schema": 1, "distribution": DISTRIBUTION, "channel": args.channel,
                    "published_at": args.published_at, "expires_at": args.expires_at,
                    "version": args.release, "url": "", "sha256": "", "size": 0,
                    "binaries": {"arm-dot": asset(binary, args.release)},
                    "rootfs": {"arm-dot": asset(rootfs, args.release)},
                    "release_artifacts": {"provenance": asset(provenance_file, args.release),
                                          "corresponding_sources": asset(source_archive, args.release)},
                    "title": f"Myshka Dot 2 {args.release}",
                    "notes": "Full A/B rootfs update with guarded announcements and signed Myshka updates.\n",
                    "release_url": f"https://github.com/{REPOSITORY}/releases/tag/{args.release}"}
        data = json_bytes(manifest)
        (output / "manifest.json").write_bytes(data)
        (output / "manifest.json.sig").write_bytes(sign(data, args.seed_file, args.public_key, args.openssl))
        sums = "".join(f"{digest(path)}  {path.name}\n" for path in sorted(output.iterdir()))
        (output / "SHA256SUMS").write_text(sums)
        output.rename(args.out_dir)
    return {"version": args.release, "manifest_sha256": digest(args.out_dir / "manifest.json"),
            "rootfs_sha256": digest(args.out_dir / rootfs.name), "output": str(args.out_dir)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("upstream-dir", "daemon", "build-record", "seed-file", "project-repo", "daemon-repo", "platform-repo", "out-dir"):
        p.add_argument("--" + name, type=Path, required=True)
    for name in ("release", "public-key", "project-commit"):
        p.add_argument("--" + name, required=True)
    for name in ("published-at", "expires-at", "source-date-epoch"):
        p.add_argument("--" + name, type=int, required=True)
    p.add_argument("--channel", choices=("beta", "stable"), required=True)
    p.add_argument("--source-extra", type=Path, action="append", default=[])
    p.add_argument("--openssl", default="openssl")
    args = p.parse_args()
    print(json.dumps(pack(args), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, tarfile.TarError) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        raise SystemExit(1)
