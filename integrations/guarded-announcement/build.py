#!/usr/bin/env python3
"""Prepare and cross-compile the pinned, experimental Dot daemon. Never deploys."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BASE = "892cdef6663acbb6ee963ed5862e363d61aff253"
UPSTREAM = "https://github.com/HuskerMinion/techo5.git"
VERSION = "v1.0.40-myshka.1.beta.1"


def run(args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(work, cache=None):
    work = work.expanduser().resolve()
    if work.exists():
        raise ValueError("Work directory must not exist; previous builds are never overwritten")
    patch = HERE / "guarded-announcement.patch"
    if not patch.is_file():
        raise ValueError("Reviewed source patch is missing")
    if cache is not None:
        cache = cache.expanduser().resolve()
        resolved = run(["git", "rev-parse", BASE + "^{commit}"], cwd=cache)
        if resolved != BASE:
            raise ValueError("Source cache does not contain the pinned commit")
    work.mkdir(parents=True)
    source = work / "source"
    run(["git", "clone", "--no-hardlinks", "--no-checkout", str(cache or UPSTREAM), str(source)])
    run(["git", "checkout", "--detach", BASE], cwd=source)
    if run(["git", "status", "--porcelain"], cwd=source):
        raise ValueError("Pinned checkout must be pristine before applying the patch")
    run(["git", "apply", "--check", str(patch)], cwd=source)
    run(["git", "apply", str(patch)], cwd=source)
    return work, source, patch


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--work-dir", required=True, type=Path)
    cli.add_argument("--source-cache", type=Path)
    cli.add_argument("--prepare-only", action="store_true")
    args = cli.parse_args()
    work, source, patch = prepare(args.work_dir, args.source_cache)
    metadata = {
        "schema": 1, "version": VERSION, "upstream": UPSTREAM,
        "upstream_commit": BASE, "patch_sha256": digest(patch),
        "target": "linux/arm/v7", "build_tags": ["dot"],
        "stage": "source-prepared", "deployed": False,
        "acoustic_acceptance": "pending", "stock_ota_image": False,
    }
    if not args.prepare_only:
        env = os.environ.copy()
        env.update(GOOS="linux", GOARCH="arm", GOARM="7", CGO_ENABLED="0")
        # Stable source date and explicit downstream version. An unsigned development
        # daemon must never identify itself as the official upstream release.
        date = run(["git", "show", "-s", "--format=%cI", BASE], cwd=source)
        package = "github.com/HuskerMinion/techo5/echod/internal/layout"
        flags = (f"-s -w -X {package}.Version={VERSION} "
                 f"-X {package}.GitCommit={BASE}-myshka-{digest(patch)[:12]} "
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
