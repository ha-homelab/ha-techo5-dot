#!/usr/bin/env python3
"""Fetch the small, hash-pinned TECHO5 interpreter for offline parity tests.

Does not fetch models, datasets, firmware or executable binaries. Does not build
or execute fetched source. Use a private destination outside the Git checkout.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import urllib.request


HERE = Path(__file__).resolve().parent
MAX_FILE_BYTES = 128 << 10
MAX_TOTAL_BYTES = 256 << 10


def fetch(destination, lock_path=HERE / "upstream-runtime-lock.json"):
    os.umask(0o077)
    lock = json.loads(lock_path.read_text())
    revision = lock["revision"]
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Expected a complete pinned commit hash")
    if lock["repository"] != "https://github.com/HuskerMinion/techo5":
        raise ValueError("Unexpected upstream repository")
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    total = 0
    for source, expected in lock["files"].items():
        if source == "LICENSE":
            relative = Path("UPSTREAM-LICENSE")
        else:
            path = PurePosixPath(source)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unexpected source path")
            if source.startswith("echod/internal/lib/tflite/"):
                relative = Path("tflite") / path.name
            elif source.startswith("echod/internal/lib/vec/"):
                relative = Path("internal/lib/vec") / path.name
            else:
                raise ValueError("Source outside the reviewed interpreter")
            if path.suffix not in (".go", ".s") or path.name.endswith("_test.go"):
                raise ValueError("Unexpected source type")
        if not 0 < expected["bytes"] <= MAX_FILE_BYTES:
            raise ValueError("Source file exceeds the download limit")
        url = f"https://raw.githubusercontent.com/HuskerMinion/techo5/{revision}/{source}"
        with urllib.request.urlopen(url, timeout=20) as response:
            data = response.read(MAX_FILE_BYTES + 1)
        total += len(data)
        if total > MAX_TOTAL_BYTES or len(data) != expected["bytes"]:
            raise ValueError("Source download size mismatch")
        if hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError("Source download hash mismatch")
        target = destination / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    for name, data in {
        "main.go": (HERE / "parity_runtime.go").read_bytes(),
        "go.mod": b"module github.com/HuskerMinion/techo5/echod\n\ngo 1.25.0\n",
        "SOURCE.json": (json.dumps(lock, indent=2) + "\n").encode(),
    }.items():
        with (destination / name).open("xb") as stream:
            stream.write(data)
    return {"revision": revision, "downloaded_bytes": total, "files": len(lock["files"])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destination", type=Path, required=True,
                   help="New directory; its parent must exist")
    a = p.parse_args()
    print(json.dumps(fetch(a.destination), indent=2))


if __name__ == "__main__":
    main()
