#!/usr/bin/env python3
"""Bounded offline parity: private existing embeddings, ONNX Runtime, TECHO5 Go.

No training or model selection. All validation owner clips are included; two
deterministically chosen synthetic subsets and a bounded background sample are
added. These are development regression data, not a fresh acoustic acceptance
set. Audio, embeddings and predictions are not copied into the report.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
import onnxruntime as ort

from export_oww_tflite import write_exclusive_files

MAX_WINDOWS = 50000


def bounded_int(low, high):
    def parse(value):
        n = int(value)
        if not low <= n <= high:
            raise argparse.ArgumentTypeError(f"expected {low} through {high}")
        return n
    return parse


def tolerance(value):
    n = float(value)
    if not np.isfinite(n) or not 0 < n <= 1e-3:
        raise argparse.ArgumentTypeError("tolerance must be finite, positive and at most 0.001")
    return n


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--onnx", type=Path, required=True)
    p.add_argument("--tflite", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--synthetic-per-label", type=bounded_int(1, 256), default=64)
    p.add_argument("--background-windows", type=bounded_int(1, 4096), default=512)
    p.add_argument("--absolute-tolerance", type=tolerance, default=1e-5)
    a = p.parse_args()
    if a.report.exists():
        p.error("Refusing to overwrite a parity report")
    if (a.work / "sources.json").stat().st_size > 16 << 20:
        p.error("Source manifest exceeds 16 MiB")
    all_rows = json.loads((a.work / "sources.json").read_text())
    if not isinstance(all_rows, list) or len(all_rows) > 20000:
        p.error("Expected at most 20,000 source manifest rows")
    validation = [r for r in all_rows if r["split"] == "val"]
    rows = [r for r in validation if r["kind"] == "owner"]
    for label in (0, 1):
        candidates = [r for r in validation if r["kind"] == "synthetic" and r["label"] == label]
        candidates.sort(key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())
        rows.extend(candidates[:a.synthetic_per_label])
    arrays, groups, provenance = [], [], []
    for row in rows:
        if not isinstance(row["id"], str) or Path(row["id"]).name != row["id"] or row["id"] in (".", ".."):
            raise ValueError("A source ID must be a plain filename stem")
        source = a.work / "features-val" / (row["id"] + ".npz")
        with np.load(source) as z:
            x = np.array(z["x"], dtype="<f4")
        if x.ndim != 3 or tuple(x.shape[1:]) != (16, 96) or not 0 < len(x) <= 5000 or not np.isfinite(x).all():
            raise ValueError("Invalid feature shape or values")
        if len(groups) + len(x) > MAX_WINDOWS:
            raise ValueError("Selected data exceeds the 50,000-window verification limit")
        arrays.append(x)
        groups.extend([f"{row['kind']}_{row['label']}"] * len(x))
        provenance.append({"id_sha256": hashlib.sha256(row["id"].encode()).hexdigest(),
                           "feature_sha256": digest(source), "windows": len(x)})
    bg = np.load(a.work / "negative-validation.npy", mmap_mode="r")
    if bg.ndim != 2 or bg.shape[1] != 96 or len(bg) < 16:
        raise ValueError("Expected continuous 96-wide background embeddings")
    if a.background_windows > len(bg) - 15:
        raise ValueError("Background sample count exceeds available distinct windows")
    indices = np.linspace(0, len(bg) - 16, a.background_windows, dtype=np.int64)
    background = np.stack([bg[i:i+16] for i in indices]).astype("<f4")
    if not np.isfinite(background).all():
        raise ValueError("Non-finite background features")
    arrays.append(background)
    groups.extend(["background"] * len(indices))
    rng = np.random.default_rng(20261025)
    controls = np.concatenate([np.zeros((1, 16, 96), dtype=np.float32),
                               rng.normal(0, .1, (8, 16, 96)),
                               rng.normal(0, 1, (8, 16, 96)),
                               rng.normal(0, 5, (8, 16, 96))]).astype("<f4")
    arrays.append(controls)
    groups.extend(["numeric_controls"] * len(controls))
    if len(groups) > MAX_WINDOWS:
        raise ValueError("Selected data exceeds the 50,000-window verification limit")
    x = np.ascontiguousarray(np.concatenate(arrays), dtype="<f4")
    opt = ort.SessionOptions()
    opt.intra_op_num_threads = 2
    opt.inter_op_num_threads = 1
    session = ort.InferenceSession(str(a.onnx), sess_options=opt, providers=["CPUExecutionProvider"])
    expected = np.concatenate([session.run(None, {"input": x[i:i+256]})[0].reshape(-1)
                               for i in range(0, len(x), 256)])
    if len(expected) != len(x) or not np.isfinite(expected).all():
        raise RuntimeError("Invalid or non-finite ONNX reference output")
    started = time.monotonic()
    result = subprocess.run([str(a.runtime.resolve()), str(a.tflite.resolve())],
                            input=x.tobytes(), capture_output=True, timeout=180)
    elapsed = time.monotonic() - started
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    actual = np.frombuffer(result.stdout, dtype="<f4")
    if len(actual) != len(expected) or not np.isfinite(actual).all():
        raise RuntimeError("Invalid runtime output")
    differences = np.abs(expected - actual)
    wrong = (expected >= .5) != (actual >= .5)
    group_array = np.array(groups)
    summary = {}
    for group in sorted(set(groups)):
        mask = group_array == group
        summary[group] = {"windows": int(mask.sum()), "max_absolute_error": float(differences[mask].max()),
                          "decision_differences": int(wrong[mask].sum()),
                          "onnx_positive_windows": int((expected[mask] >= .5).sum()),
                          "tflite_positive_windows": int((actual[mask] >= .5).sum()),
                          "closest_onnx_distance_to_threshold": float(abs(expected[mask] - .5).min())}
    report = {
        "passed": bool(differences.max() <= a.absolute_tolerance and not wrong.any()),
        "source_onnx_sha256": digest(a.onnx), "tflite_sha256": digest(a.tflite),
        "runtime_sha256": digest(a.runtime), "source_manifest_sha256": digest(a.work / "sources.json"),
        "source_feature_selection_sha256": hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest(),
        "source_clips": dict(Counter(f"{r['kind']}_{r['label']}" for r in rows)),
        "windows": len(x), "threshold": .5, "absolute_tolerance": a.absolute_tolerance,
        "max_absolute_error": float(differences.max()), "decision_differences": int(wrong.sum()),
        "groups": summary, "runtime_seconds_host_only": elapsed,
        "onnxruntime_version": ort.__version__, "full_audio_frontend_tested": False,
        "device_runtime_tested": False, "fresh_independent_acoustic_test": False,
        "scope": "Bounded existing development/validation embeddings; no retraining or corpus generation.",
    }
    write_exclusive_files([(a.report, (json.dumps(report, indent=2) + "\n").encode())])
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
