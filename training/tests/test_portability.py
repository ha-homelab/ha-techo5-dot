"""Synthetic tests; no household model, recordings or datasets are needed."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import onnx
from onnx import helper as h, numpy_helper as nh, TensorProto as T
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_oww_tflite as exporter
import verify_oww_tflite as verifier


def synthetic_model():
    """Independent ONNX expression of the documented head, with random weights."""
    rng = np.random.default_rng(20261025)
    weights = []
    for index, dims in [(1, (256, 1536)), (5, (256, 256)), (9, (1, 256))]:
        weights.append(nh.from_array(rng.normal(0, .035, dims).astype(np.float32), f"classifier.layers.{index}.weight"))
        weights.append(nh.from_array(np.zeros(dims[0], np.float32), f"classifier.layers.{index}.bias"))
    for index in (2, 6):
        weights.append(nh.from_array(rng.uniform(.8, 1.2, 256).astype(np.float32), f"classifier.layers.{index}.weight"))
        weights.append(nh.from_array(rng.normal(0, .02, 256).astype(np.float32), f"classifier.layers.{index}.bias"))
    weights.append(nh.from_array(np.array(-.1, np.float32), "calibration_logit_offset"))
    nodes = []
    for n, end in enumerate((1, -1)):
        args = []
        for label, value in [("start", 0), ("end", end), ("axis", 1), ("stride", 1)]:
            name = f"slice{n}_{label}"
            nodes.append(h.make_node("Constant", [], [name], value=nh.from_array(np.array([value], np.int64))))
            args.append(name)
        nodes.append(h.make_node("Slice", ["input"] + args, [f"slice{n}"]))
    nodes.append(h.make_node("Concat", ["slice0", "slice1"], ["preceding"], axis=1))
    logits = []
    for name, input_name in [("current", "input"), ("previous", "preceding")]:
        x = name + "_flat"
        nodes.append(h.make_node("Flatten", [input_name], [x], axis=1))
        for index, norm in [(1, 2), (5, 6), (9, None)]:
            y = f"{name}_dense{index}"
            nodes.append(h.make_node("Gemm", [x, f"classifier.layers.{index}.weight", f"classifier.layers.{index}.bias"],
                                     [y], alpha=1., beta=1., transB=1))
            x = y
            if norm is not None:
                y = f"{name}_norm{norm}"
                nodes.append(h.make_node("LayerNormalization", [x, f"classifier.layers.{norm}.weight", f"classifier.layers.{norm}.bias"],
                                         [y], axis=-1, epsilon=1e-5))
                x = f"{name}_relu{norm}"
                nodes.append(h.make_node("Relu", [y], [x]))
        logits.append(x)
    nodes.extend([h.make_node("Min", logits, ["confirmed"]),
                  h.make_node("Add", ["confirmed", "calibration_logit_offset"], ["calibrated"]),
                  h.make_node("Sigmoid", ["calibrated"], ["score"])])
    model = h.make_model(h.make_graph(nodes, "synthetic_confirmed", [h.make_tensor_value_info("input", T.FLOAT, [None, 16, 96])],
                                    [h.make_tensor_value_info("score", T.FLOAT, [None, 1])], weights),
                         opset_imports=[h.make_opsetid("", 17)])
    model.ir_version = 10
    return model


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.onnx"
        self.target = self.root / "output.tflite"
        self.model = synthetic_model()
        onnx.save(self.model, self.source)

    def export(self):
        return exporter.export(self.source, self.target, hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_export_has_expected_shape_and_private_permissions(self):
        report = self.export()
        self.assertEqual(report["input_shape"], [1, 16, 96])
        self.assertEqual(report["operators"]["MINIMUM"], 1)
        self.assertEqual(report["operators"]["PACK"], 1)
        self.assertEqual(self.target.read_bytes()[4:8], b"TFL3")
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.target.with_suffix(".export.json").stat().st_mode & 0o777, 0o600)

    def test_wrong_source_hash_creates_no_outputs(self):
        with self.assertRaisesRegex(ValueError, "hash differs"):
            exporter.export(self.source, self.target, "0" * 64)
        self.assertFalse(self.target.exists())

    def test_existing_receipt_is_not_overwritten(self):
        receipt = self.target.with_suffix(".export.json")
        receipt.write_text("keep this")
        with self.assertRaises(FileExistsError):
            self.export()
        self.assertEqual(receipt.read_text(), "keep this")
        self.assertFalse(self.target.exists())

    def test_unique_display_label_does_not_change_classifier(self):
        self.export()
        labeled = self.root / "personal.tflite"
        report = exporter.export(self.source, labeled, hashlib.sha256(self.source.read_bytes()).hexdigest(),
                                 display_label="Привет, Мышка (personal)", languages=["ru"])
        sidecar = labeled.with_suffix(".json")
        manifest = json.loads(sidecar.read_text())
        self.assertEqual(self.target.read_bytes(), labeled.read_bytes())
        self.assertEqual(manifest["wake_word"], "Привет, Мышка (personal)")
        self.assertEqual(manifest["model"], "personal.tflite")
        self.assertEqual(manifest["trained_languages"], ["ru"])
        self.assertEqual(manifest["recommended_threshold"], .5)
        self.assertEqual(report["manifest_sha256"], hashlib.sha256(sidecar.read_bytes()).hexdigest())
        self.assertEqual(sidecar.stat().st_mode & 0o777, 0o600)

    def test_existing_manifest_blocks_all_new_outputs(self):
        sidecar = self.target.with_suffix(".json")
        sidecar.write_text("keep this")
        with self.assertRaises(FileExistsError):
            exporter.export(self.source, self.target, hashlib.sha256(self.source.read_bytes()).hexdigest(),
                            display_label="Привет, Мышка (personal)", languages=["ru"])
        self.assertEqual(sidecar.read_text(), "keep this")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.target.with_suffix(".export.json").exists())

    def test_manifest_metadata_requires_label_and_explicit_language(self):
        for label, languages in [("", ["ru"]), ("word\nother", ["ru"]),
                                 ("word", None), (None, ["ru"]), ("word", ["not a tag"])]:
            with self.subTest(label=label, languages=languages), self.assertRaises(ValueError):
                exporter.export(self.source, self.target, hashlib.sha256(self.source.read_bytes()).hexdigest(),
                                display_label=label, languages=languages)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["source.onnx"])

    def test_same_operator_count_wrong_shift_is_rejected(self):
        node = next(n for n in self.model.graph.node if list(n.output) == ["slice1_end"])
        node.attribute[0].t.CopyFrom(nh.from_array(np.array([-2], np.int64)))
        onnx.save(self.model, self.source)
        with self.assertRaisesRegex(ValueError, "slice does not match"):
            self.export()

    def test_nonfinite_weights_are_rejected(self):
        value = nh.to_array(self.model.graph.initializer[0]).copy()
        value[0, 0] = np.nan
        self.model.graph.initializer[0].CopyFrom(nh.from_array(value, self.model.graph.initializer[0].name))
        onnx.save(self.model, self.source)
        with self.assertRaisesRegex(ValueError, "finite float32"):
            self.export()

    @unittest.skipUnless(os.getenv("TECHO5_PARITY_RUNTIME"), "Set TECHO5_PARITY_RUNTIME to the compiled pinned harness")
    def test_synthetic_end_to_end_parity(self):
        self.export()
        rng = np.random.default_rng(92)
        ordinary = rng.normal(0, 1, (128, 16, 96)).astype("<f4")
        x = np.concatenate([ordinary, ordinary[:, ::-1, :], np.zeros((1, 16, 96), "<f4")])
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        session = ort.InferenceSession(str(self.source), sess_options=opts, providers=["CPUExecutionProvider"])
        expected = session.run(None, {"input": x})[0].reshape(-1)
        result = subprocess.run([os.environ["TECHO5_PARITY_RUNTIME"], str(self.target)], input=x.tobytes(),
                                capture_output=True, check=True, timeout=30)
        actual = np.frombuffer(result.stdout, "<f4")
        self.assertEqual(len(expected), len(actual))
        self.assertTrue(np.isfinite(actual).all())
        self.assertLessEqual(float(np.max(np.abs(expected - actual))), 1e-5)
        np.testing.assert_array_equal(expected >= .5, actual >= .5)
        self.assertGreater(int((expected >= .5).sum()), 0)
        self.assertGreater(int((expected < .5).sum()), 0)
        # Ensure these fixtures can distinguish confirmation from one-view inference.
        single = copy.deepcopy(self.model)
        add = next(n for n in single.graph.node if n.op_type == "Add")
        add.input[0] = "current_dense9"
        one = ort.InferenceSession(single.SerializeToString(), sess_options=opts, providers=["CPUExecutionProvider"])
        single_score = one.run(None, {"input": x})[0].reshape(-1)
        self.assertGreater(float(np.max(single_score - expected)), .05)


class VerifierGuardTests(unittest.TestCase):
    def test_cli_bounds_and_finite_tolerance(self):
        for value in ("-1", "0", "257"):
            with self.assertRaises(argparse.ArgumentTypeError):
                verifier.bounded_int(1, 256)(value)
        for value in ("nan", "inf", "0", "-1", ".1"):
            with self.assertRaises(argparse.ArgumentTypeError):
                verifier.tolerance(value)

    def work(self, root, background_frames):
        (root / "features-val").mkdir()
        (root / "sources.json").write_text(json.dumps([{"id": "synthetic_owner_fixture", "split": "val", "kind": "owner", "label": 1}]))
        np.savez(root / "features-val/synthetic_owner_fixture.npz", x=np.zeros((1, 16, 96), np.float32))
        np.save(root / "negative-validation.npy", np.zeros((background_frames, 96), np.float32))
        return ["verify", "--work", str(root), "--onnx", str(root / "unused.onnx"), "--tflite", str(root / "unused.tflite"),
                "--runtime", str(root / "unused_runtime"), "--report", str(root / "result.json"), "--background-windows", "1"]

    def test_short_background_rejected_before_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = self.work(Path(tmp), 15)
            with patch.object(sys, "argv", argv), patch.object(verifier.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "continuous 96-wide"):
                    verifier.main()
                run.assert_not_called()

    def test_nonfinite_reference_rejected_before_comparison(self):
        class InvalidReference:
            def run(self, _, inputs):
                return [np.full((len(inputs["input"]), 1), np.nan, np.float32)]
        with tempfile.TemporaryDirectory() as tmp:
            argv = self.work(Path(tmp), 16)
            with patch.object(sys, "argv", argv), patch.object(verifier.ort, "InferenceSession", return_value=InvalidReference()), \
                    patch.object(verifier.subprocess, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "non-finite ONNX"):
                    verifier.main()
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
