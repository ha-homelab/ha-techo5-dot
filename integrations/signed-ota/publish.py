#!/usr/bin/env python3
"""Verify, publish, then promote a locally signed Myshka release with gh.

No signing key is read. Version assets are never overwritten. Channel metadata
is promoted only after downloading and hashing every immutable release asset.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

REPO = "ha-homelab/ha-techo5-dot"
PUBLIC_KEY = "VE1OZ3bqYzfSexvgIBbi6lGMkZW1VV22jnTTbogJBNw="
VERSION = re.compile(r"v\d+\.\d+\.\d+(?:-beta\.[1-9]\d*)?_myshka[1-9]\d*")


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def signature(directory):
    openssl = os.environ.get("OPENSSL", "openssl")
    with tempfile.TemporaryDirectory(prefix="myshka-signature-") as scratch:
        root = Path(scratch)
        # RFC 8410 SubjectPublicKeyInfo for Ed25519.
        (root / "public.der").write_bytes(bytes.fromhex("302a300506032b6570032100") + base64.b64decode(PUBLIC_KEY, validate=True))
        (root / "signature").write_bytes(base64.b64decode((directory / "manifest.json.sig").read_bytes().strip(), validate=True))
        run(openssl, "pkeyutl", "-verify", "-pubin", "-keyform", "DER", "-inkey", str(root / "public.der"),
            "-rawin", "-in", str(directory / "manifest.json"), "-sigfile", str(root / "signature"))


def verify(directory):
    directory = directory.resolve()
    files = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if not match:
            raise ValueError("Malformed checksum list")
        digest, name = match.groups()
        file = directory / name
        if name in files or file.is_symlink() or not file.is_file() or sha(file) != digest:
            raise ValueError("Duplicate, missing or corrupt asset: " + name)
        files[name] = digest
    signature(directory)
    m = json.loads((directory / "manifest.json").read_text())
    version = m.get("version", "")
    match = VERSION.fullmatch(version)
    if not match or ("beta" if "-beta." in version else "stable") != m.get("channel") or m.get("distribution") != "myshka-dot2" or m.get("schema") != 1:
        raise ValueError("Wrong signed distribution, version or channel")
    now = time.time()
    if not 0 < m["published_at"] <= now + 600 or not now < m["expires_at"] <= m["published_at"] + 366 * 86400:
        raise ValueError("Expired or invalid signed lifetime")
    required = {"manifest.json", "manifest.json.sig"}
    if set(m.get("release_artifacts", {})) != {"provenance", "corresponding_sources"}:
        raise ValueError("Signed source and provenance records are required")
    expected_metadata = {"provenance": "release-provenance.json",
                         "corresponding_sources": f"myshka-corresponding-sources-{version}.tar.gz"}
    for key, expected in expected_metadata.items():
        entry = m["release_artifacts"][key]
        if (entry["url"] != f"https://github.com/{REPO}/releases/download/{version}/{expected}"
                or entry["sha256"] != files.get(expected)
                or entry["size"] != (directory / expected).stat().st_size):
            raise ValueError("Signed provenance or corresponding sources differ")
        required.add(expected)
    for kind in ("binaries", "rootfs"):
        if set(m[kind]) != {"arm-dot"}:
            raise ValueError("Only Dot 2 arm-dot releases are supported")
        entry = m[kind]["arm-dot"]
        name = entry["url"].rsplit("/", 1)[-1]
        if entry["url"] != f"https://github.com/{REPO}/releases/download/{version}/{name}":
            raise ValueError("Asset URL is not in the immutable own-repository release")
        required.add(name)
        if files.get(name) != entry["sha256"] or (directory / name).stat().st_size != entry["size"]:
            raise ValueError("Signed asset digest or size differs")
    if set(files) != required:
        raise ValueError("Release asset inventory differs from the public allowlist")
    actual = {p.name for p in directory.iterdir()}
    if actual != required | {"SHA256SUMS"}:
        raise ValueError("Unlisted files in release directory; refusing publication")
    return m, files


def release(tag):
    p = subprocess.run(["gh", "api", f"repos/{REPO}/releases/tags/{tag}"], capture_output=True, text=True)
    if p.returncode == 0:
        return json.loads(p.stdout)
    if "(HTTP 404)" not in p.stderr:
        raise RuntimeError("Cannot establish release state: " + p.stderr)
    return None


def version_key(version):
    if not VERSION.fullmatch(version):
        raise ValueError("Invalid channel version")
    base, _, _suffix = version[1:].partition("_")
    core, sep, beta = base.partition("-beta.")
    return (*map(int, core.split(".")), 0 if sep else 1, int(beta) if sep else 0)


def remote_verified(tag, local, names):
    with tempfile.TemporaryDirectory(prefix="myshka-release-") as scratch:
        command = ["gh", "release", "download", tag, "--repo", REPO, "--dir", scratch]
        for name in names:
            command.extend(["--pattern", name])
        subprocess.run(command, check=True)
        for name in names:
            if sha(Path(scratch) / name) != sha(local / name):
                raise ValueError("Remote asset mismatch: " + name)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    cli.add_argument("--publish", action="store_true", help="create immutable version release")
    cli.add_argument("--promote", action="store_true", help="point own channel at verified release")
    cli.add_argument("--target", help="exact pushed source commit; required for publication")
    cli.add_argument("--notes-file", type=Path)
    args = cli.parse_args()
    m, checksums = verify(args.directory)
    print("Local signature, hashes, target and asset inventory verified", flush=True)
    if not (args.publish or args.promote):
        return
    version = m["version"]
    assets = sorted(set(checksums) | {"SHA256SUMS"})
    provenance = json.loads((args.directory / "release-provenance.json").read_text())
    source_commit = provenance.get("project_commit", "")
    if not re.fullmatch(r"[a-f0-9]{40}", source_commit):
        raise ValueError("Signed provenance lacks an exact source commit")
    existing = release(version)
    if args.publish:
        if not args.target or not re.fullmatch(r"[a-f0-9]{40}", args.target) or not args.notes_file:
            raise ValueError("Publication requires exact commit and reviewed notes file")
        # The packaging record is the source of the exact schema. Also require
        # the target to exist upstream so gh cannot silently publish local code.
        resolved = json.loads(run("gh", "api", f"repos/{REPO}/commits/{args.target}"))["sha"]
        if resolved != args.target or args.target != provenance.get("project_commit"):
            raise ValueError("Published source commit differs from packaged provenance")
        if existing is None:
            command = ["gh", "release", "create", version, "--repo", REPO, "--target", args.target,
                       "--title", "Myshka Dot 2 " + version, "--notes-file", str(args.notes_file), "--latest=false"]
            if m["channel"] == "beta":
                command.append("--prerelease")
            command.extend(str(args.directory / name) for name in assets)
            subprocess.run(command, check=True)
        elif existing.get("draft"):
            raise ValueError("Existing draft must be reviewed explicitly; not overwriting")
    published = release(version)
    if published is None or published.get("draft"):
        raise ValueError("Immutable release must exist before promotion")
    tagged_commit = json.loads(run("gh", "api", f"repos/{REPO}/commits/{version}"))["sha"]
    if tagged_commit != source_commit:
        raise ValueError("Release tag differs from the signed source commit")
    remote_verified(version, args.directory, assets)
    print("Published version assets verified by downloading every asset", flush=True)
    if args.promote:
        tag = "myshka-" + m["channel"]
        current = release(tag)
        metadata = [str(args.directory / n) for n in ("manifest.json", "manifest.json.sig")]
        if current is None:
            if not args.target:
                raise ValueError("First channel publication requires a target commit")
            subprocess.run(["gh", "release", "create", tag, "--repo", REPO, "--target", args.target,
                            "--title", "Myshka Dot 2 " + m["channel"] + " channel",
                            "--notes", "Signed update feed. Immutable firmware assets are linked by the manifest. Do not install this channel on stock firmware.",
                            "--prerelease", "--latest=false", *metadata], check=True)
        else:
            with tempfile.TemporaryDirectory(prefix="myshka-current-") as scratch:
                subprocess.run(["gh", "release", "download", tag, "--repo", REPO, "--dir", scratch,
                                "--pattern", "manifest.json", "--pattern", "manifest.json.sig"], check=True)
                old_dir = Path(scratch)
                signature(old_dir)
                old = json.loads((old_dir / "manifest.json").read_text())
                if (old.get("channel") != m["channel"] or old.get("distribution") != m["distribution"]
                        or old["published_at"] > m["published_at"] or version_key(old["version"]) > version_key(version)):
                    raise ValueError("Refusing cross-channel metadata or a channel downgrade")
            subprocess.run(["gh", "release", "upload", tag, "--repo", REPO, "--clobber", *metadata], check=True)
        remote_verified(tag, args.directory, ["manifest.json", "manifest.json.sig"])
        print("Own signed channel promoted and read back. Device installation remains explicit.")


if __name__ == "__main__":
    main()
