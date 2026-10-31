#!/usr/bin/env python3
"""Build the pinned Myshka Dot 2 daemon with guarded audio and signed OTA. Never deploys."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
BASE = "b6a070fc6e62ec0e2636726619003e8c6505c4f8"
UPSTREAM = "https://github.com/HuskerMinion/techo5.git"
VERSION = "v1.0.44-beta.202_myshka2"
PUBLIC_KEY = "VE1OZ3bqYzfSexvgIBbi6lGMkZW1VV22jnTTbogJBNw="
DISTRIBUTION = "myshka-dot2"
VERSION_RE = re.compile(r"v1\.0\.44(?:-beta\.[1-9][0-9]{0,8})?_myshka2\Z")


def run(args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(work, cache=None):
    work = work.expanduser().resolve()
    if work.exists():
        raise ValueError("Work directory must not exist; prior builds are never overwritten")
    guarded = HERE.parent / "guarded-announcement" / "guarded-announcement.patch"
    native = HERE / "native.patch"
    for patch in (guarded, native):
        if not patch.is_file():
            raise ValueError(f"Reviewed source patch is missing: {patch.name}")
    if cache is not None:
        cache = cache.expanduser().resolve()
        if run(["git", "rev-parse", BASE + "^{commit}"], cwd=cache) != BASE:
            raise ValueError("Source cache does not contain the pinned upstream commit")
    work.mkdir(parents=True)
    source = work / "source"
    run(["git", "clone", "--no-hardlinks", "--no-checkout", str(cache or UPSTREAM), str(source)])
    run(["git", "checkout", "--detach", BASE], cwd=source)
    if run(["git", "status", "--porcelain"], cwd=source):
        raise ValueError("Pinned checkout must be pristine")
    for patch in (guarded, native):
        run(["git", "apply", "--check", str(patch)], cwd=source)
        run(["git", "apply", str(patch)], cwd=source)
    trust = source / "echod/internal/update/trust.go"
    if f'var releaseKey = "{PUBLIC_KEY}"' not in trust.read_text():
        raise ValueError("Source does not contain the fixed Myshka trust anchor")
    return work, source, guarded, native


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--work-dir", required=True, type=Path)
    cli.add_argument("--source-cache", type=Path)
    cli.add_argument("--version", default=VERSION)
    cli.add_argument("--prepare-only", action="store_true")
    args = cli.parse_args()
    if not VERSION_RE.fullmatch(args.version):
        cli.error("version must be v1.0.44-beta.N_myshka2 or v1.0.44_myshka2")
    work, source, guarded, native = prepare(args.work_dir, args.source_cache)
    metadata = {
        "schema": 1, "version": args.version, "distribution": DISTRIBUTION,
        "release_public_key": PUBLIC_KEY, "upstream": UPSTREAM, "upstream_commit": BASE,
        "patch_sha256": digest(guarded), "ota_patch_sha256": digest(native),
        "target": "linux/arm/v7", "build_tags": ["dot"],
        "stage": "source-prepared", "deployed": False,
        "stock_ota_image": False, "acoustic_acceptance": "pending",
    }
    if not args.prepare_only:
        env = os.environ.copy()
        env.update(GOOS="linux", GOARCH="arm", GOARM="7", CGO_ENABLED="0")
        date = run(["git", "show", "-s", "--format=%cI", BASE], cwd=source)
        package = "github.com/HuskerMinion/techo5/echod/internal/layout"
        flags = (f"-s -w -X {package}.Version={args.version} "
                 f"-X {package}.GitCommit={BASE}-myshka-{digest(native)[:12]} "
                 f"-X {package}.BuildDate={date}")
        output = work / "echod-arm-dot"
        run(["go", "build", "-buildvcs=false", "-trimpath", "-tags", "dot",
             "-ldflags", flags, "-o", str(output), "./cmd/echod"],
            cwd=source / "echod", env=env)
        metadata.update(stage="compiled", binary_sha256=digest(output),
                        binary_bytes=output.stat().st_size,
                        go_version=run(["go", "version"]))
    (work / "build.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
