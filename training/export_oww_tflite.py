#!/usr/bin/env python3
"""Export a confirmed, calibrated OWW dense head without TensorFlow or training.

This deliberately supports one audited architecture, not arbitrary ONNX graphs.
The input is a private ONNX head with two shared-weight 256-wide LayerNorm/ReLU
branches, the repeated-oldest shifted view, min confirmation, and logit offset.
It emits float32 TFLite for TECHO5's small interpreter. No quantization occurs.
Requires numpy, onnx, flatbuffers and the small tflite schema package (2.18.0).
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re

import flatbuffers
import numpy as np
import onnx
from onnx import numpy_helper
import tflite as tf


class Graph:
    def __init__(self):
        self.tensors, self.ops, self.buffers = [], [], [b""]

    def tensor(self, name, shape, value=None, integer=False):
        buf = 0
        if value is not None:
            value = np.asarray(value, dtype="<i4" if integer else "<f4")
            assert tuple(value.shape) == tuple(shape), (name, value.shape, shape)
            buf = len(self.buffers)
            self.buffers.append(value.tobytes())
        self.tensors.append((name, shape, buf, tf.TensorType.INT32 if integer else tf.TensorType.FLOAT32))
        return len(self.tensors) - 1

    def const(self, name, value, integer=False):
        value = np.asarray(value, dtype="<i4" if integer else "<f4")
        return self.tensor(name, list(value.shape), value, integer)

    def op(self, kind, args, name, shape, options=None):
        out = self.tensor(name, shape)
        self.ops.append((kind, args, [out], options))
        return out

    def serialize(self, input_id, output_id):
        b = flatbuffers.Builder(2 << 20)

        def vector(values, offsets=False):
            b.StartVector(4, len(values), 4)
            for value in reversed(values):
                (b.PrependUOffsetTRelative if offsets else b.PrependInt32)(value)
            return b.EndVector()

        def options(kind, fields):
            getattr(tf, kind + "Start")(b)
            for key, value in fields.items():
                getattr(tf, kind + "Add" + key)(b, value)
            return getattr(tf, kind + "End")(b)

        codes = list(dict.fromkeys(op[0] for op in self.ops))
        opcode_offsets = []
        for code in codes:
            builtin = getattr(tf.BuiltinOperator, code)
            tf.OperatorCodeStart(b)
            tf.OperatorCodeAddBuiltinCode(b, builtin)
            tf.OperatorCodeAddDeprecatedBuiltinCode(b, min(builtin, 127))
            tf.OperatorCodeAddVersion(b, 1)
            opcode_offsets.append(tf.OperatorCodeEnd(b))
        tensor_offsets = []
        for name, shape, buf, dtype in self.tensors:
            name_offset, shape_offset = b.CreateString(name), vector(shape)
            tf.TensorStart(b)
            tf.TensorAddName(b, name_offset)
            tf.TensorAddShape(b, shape_offset)
            tf.TensorAddType(b, dtype)
            tf.TensorAddBuffer(b, buf)
            tensor_offsets.append(tf.TensorEnd(b))
        op_offsets = []
        for code, inputs, outputs, opt in self.ops:
            oi, oo = vector(inputs), vector(outputs)
            option_offset, option_type = 0, 0
            if opt:
                kind, fields = opt
                fields = dict(fields)
                if kind == "ReshapeOptions":
                    fields["NewShape"] = vector(fields["NewShape"])
                option_offset = options(kind, fields)
                option_type = getattr(tf.BuiltinOptions, kind)
            tf.OperatorStart(b)
            tf.OperatorAddOpcodeIndex(b, codes.index(code))
            tf.OperatorAddInputs(b, oi)
            tf.OperatorAddOutputs(b, oo)
            if opt:
                tf.OperatorAddBuiltinOptionsType(b, option_type)
                tf.OperatorAddBuiltinOptions(b, option_offset)
            op_offsets.append(tf.OperatorEnd(b))
        tensors, ops = vector(tensor_offsets, True), vector(op_offsets, True)
        inputs, outputs = vector([input_id]), vector([output_id])
        name = b.CreateString("confirmed_calibrated_oww")
        tf.SubGraphStart(b)
        tf.SubGraphAddTensors(b, tensors)
        tf.SubGraphAddInputs(b, inputs)
        tf.SubGraphAddOutputs(b, outputs)
        tf.SubGraphAddOperators(b, ops)
        tf.SubGraphAddName(b, name)
        subgraph = tf.SubGraphEnd(b)
        buffers = []
        for raw in self.buffers:
            data = b.CreateByteVector(raw) if raw else None
            tf.BufferStart(b)
            if data is not None:
                tf.BufferAddData(b, data)
            buffers.append(tf.BufferEnd(b))
        subgraphs, opcode_vec, buffer_vec = vector([subgraph], True), vector(opcode_offsets, True), vector(buffers, True)
        description = b.CreateString("Float32 OWW dense head; repeated-oldest shifted view; min confirmation; preserved logit calibration")
        tf.ModelStart(b)
        tf.ModelAddVersion(b, 3)
        tf.ModelAddOperatorCodes(b, opcode_vec)
        tf.ModelAddSubgraphs(b, subgraphs)
        tf.ModelAddBuffers(b, buffer_vec)
        tf.ModelAddDescription(b, description)
        b.Finish(tf.ModelEnd(b), file_identifier=b"TFL3")
        return bytes(b.Output())


def write_exclusive_files(files):
    """Reserve every output before writing; never truncate a caller's file."""
    opened = []
    try:
        for path, data in files:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            opened.append((Path(path), fd, data))
        for _, fd, data in opened:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(fd)
    except BaseException:
        for path, _, _ in opened:
            path.unlink(missing_ok=True)
        raise
    finally:
        for _, fd, _ in opened:
            os.close(fd)


def check_wiring(model):
    """Check graph semantics, not just operator counts or a filename."""
    if len(model.graph.input) != 1 or len(model.graph.output) != 1:
        raise ValueError("Expected one input and one output")
    inp = model.graph.input[0]
    dims = inp.type.tensor_type.shape.dim
    if inp.type.tensor_type.elem_type != onnx.TensorProto.FLOAT or len(dims) != 3:
        raise ValueError("Expected float32 [batch,16,96] input")
    if dims[0].dim_value not in (0, 1) or [d.dim_value for d in dims[1:]] != [16, 96]:
        raise ValueError("Expected float32 [batch,16,96] input")
    nodes = {out: n for n in model.graph.node for out in n.output}

    def node(out, kind, count):
        n = nodes.get(out)
        if n is None or n.op_type != kind or len(n.input) != count or len(n.output) != 1:
            raise ValueError(f"Unsupported graph wiring at {kind}")
        return n

    def attrs(n):
        return {a.name: onnx.helper.get_attribute_value(a) for a in n.attribute}

    def constant(out, value):
        n = node(out, "Constant", 0)
        v = attrs(n).get("value")
        if v is None or not np.array_equal(numpy_helper.to_array(v), [value]):
            raise ValueError("Shifted-view slice does not match the reviewed semantics")

    sig = node(model.graph.output[0].name, "Sigmoid", 1)
    add = node(sig.input[0], "Add", 2)
    if add.input[1] != "calibration_logit_offset":
        raise ValueError("Expected final calibrated logit offset")
    minimum = node(add.input[0], "Min", 2)
    branch_inputs = []
    for branch in minimum.input:
        cursor = branch
        for layer, norm_layer in [(9, None), (5, 6), (1, 2)]:
            if norm_layer is not None:
                relu = node(cursor, "Relu", 1)
                ln = node(relu.input[0], "LayerNormalization", 3)
                a = attrs(ln)
                if a.get("axis", -1) != -1 or a.get("stash_type", 1) != 1:
                    raise ValueError("Unsupported layer normalization semantics")
                if list(ln.input[1:]) != [f"classifier.layers.{norm_layer}.weight", f"classifier.layers.{norm_layer}.bias"]:
                    raise ValueError("Unexpected normalization weights")
                cursor = ln.input[0]
            dense = node(cursor, "Gemm", 3)
            a = attrs(dense)
            if (a.get("alpha", 1.0), a.get("beta", 1.0), a.get("transA", 0), a.get("transB", 0)) != (1.0, 1.0, 0, 1):
                raise ValueError("Unsupported dense-layer semantics")
            if list(dense.input[1:]) != [f"classifier.layers.{layer}.weight", f"classifier.layers.{layer}.bias"]:
                raise ValueError("Unexpected dense-layer weights")
            cursor = dense.input[0]
        flat = node(cursor, "Flatten", 1)
        if attrs(flat).get("axis", 1) != 1:
            raise ValueError("Unsupported flatten axis")
        branch_inputs.append(flat.input[0])
    if branch_inputs[0] != inp.name:
        raise ValueError("Expected unshifted first branch")
    cat = node(branch_inputs[1], "Concat", 2)
    if attrs(cat).get("axis") != 1:
        raise ValueError("Unsupported shifted-view concatenation")
    for out, end in zip(cat.input, (1, -1)):
        sl = node(out, "Slice", 5)
        if sl.input[0] != inp.name:
            raise ValueError("Shift must use the original embeddings")
        for name, expected in zip(sl.input[1:], (0, end, 1, 1)):
            constant(name, expected)


def audited_weights(model):
    """Refuse architectural drift instead of silently exporting a different head."""
    expected = Counter(Constant=8, Slice=2, Concat=1, Flatten=2, Gemm=6,
                       LayerNormalization=4, Relu=4, Min=1, Add=1, Sigmoid=1)
    if Counter(n.op_type for n in model.graph.node) != expected:
        raise ValueError("Unsupported ONNX architecture; review exporter before proceeding")
    onnx.checker.check_model(model)
    check_wiring(model)
    weights = {v.name: numpy_helper.to_array(v) for v in model.graph.initializer}
    shapes = {
        "classifier.layers.1.weight": (256, 1536), "classifier.layers.1.bias": (256,),
        "classifier.layers.2.weight": (256,), "classifier.layers.2.bias": (256,),
        "classifier.layers.5.weight": (256, 256), "classifier.layers.5.bias": (256,),
        "classifier.layers.6.weight": (256,), "classifier.layers.6.bias": (256,),
        "classifier.layers.9.weight": (1, 256), "classifier.layers.9.bias": (1,),
        "calibration_logit_offset": (),
    }
    if set(weights) != set(shapes) or any(weights[k].shape != v for k, v in shapes.items()):
        raise ValueError("Unsupported weight names/shapes")
    if any(v.dtype != np.float32 or not np.isfinite(v).all() for v in weights.values()):
        raise ValueError("Expected finite float32 weights")
    # A required caller-provided SHA-256 also pins exact graph wiring and all attributes.
    epsilon = []
    for n in model.graph.node:
        if n.op_type == "LayerNormalization":
            attrs = {a.name: onnx.helper.get_attribute_value(a) for a in n.attribute}
            if attrs.get("axis") != -1:
                raise ValueError("Unsupported normalization axis")
            epsilon.append(attrs.get("epsilon", 1e-5))
    if len(set(epsilon)) != 1 or not np.isfinite(epsilon[0]) or not 0 < epsilon[0] <= .1:
        raise ValueError("Branch normalization epsilon differs")
    return weights, epsilon[0]


def wake_manifest(target, display_label, languages):
    """Keep HA's display label separate from the classifier and its filename ID."""
    if display_label is None:
        if languages:
            raise ValueError("--language requires --display-label")
        return None
    if target.suffix != ".tflite":
        raise ValueError("A wake-word manifest requires a .tflite output filename")
    if not display_label.strip() or any(ord(c) < 32 or ord(c) == 127 for c in display_label):
        raise ValueError("Display label must be nonempty and contain no control characters")
    if not languages or any(not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", s) for s in languages):
        raise ValueError("Supply --language with an explicit language tag, for example ru")
    return {
        "type": "openwakeword", "wake_word": display_label.strip(),
        "model": target.name, "trained_languages": list(dict.fromkeys(languages)),
        "version": 1, "recommended_threshold": 0.5,
    }


def export(source, target, expected_sha256, *, display_label=None, languages=None):
    os.umask(0o077)
    manifest = wake_manifest(target, display_label, languages)
    if source.stat().st_size > 8 << 20:
        raise ValueError("Source exceeds this architecture's 8 MiB input limit")
    report_path = target.with_suffix(".export.json")
    output_paths = [target, report_path]
    if manifest is not None:
        output_paths.append(target.with_suffix(".json"))
    if len(set(output_paths)) != len(output_paths) or any(p.exists() for p in output_paths):
        raise FileExistsError("Model, export receipt or requested manifest already exists")
    raw = source.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    if source_hash != expected_sha256:
        raise ValueError("Source hash differs from the reviewed deployed model")
    weights, eps = audited_weights(onnx.load_model_from_string(raw))
    g = Graph()
    x = g.tensor("input", [1, 16, 96])
    weight_ids = {name: g.const(name, value) for name, value in weights.items()}
    axis = g.const("normalization_axis", [-1], True)
    epsilon = g.const("normalization_epsilon", np.float32(eps))
    strides = g.const("slice_strides", [1, 1, 1], True)
    # PACK substitutes for CONCATENATION, which is not implemented by the pinned
    # TECHO5 interpreter. The repeated first frame is exact, not weight folding.
    frames = []
    for k in range(15):
        begin = g.const(f"begin_{k}", [0, k, 0], True)
        end = g.const(f"end_{k}", [1, k + 1, 96], True)
        frames.append(g.op("STRIDED_SLICE", [x, begin, end, strides], f"frame_{k}", [1, 1, 96],
                           ("StridedSliceOptions", {})))
    packed = g.op("PACK", [frames[0]] + frames, "preceding_packed", [1, 16, 1, 96],
                  ("PackOptions", {"ValuesCount": 16, "Axis": 1}))
    previous = g.op("RESHAPE", [packed], "preceding", [1, 16, 96],
                    ("ReshapeOptions", {"NewShape": [1, 16, 96]}))

    def linear(inp, layer, name, out_width):
        return g.op("FULLY_CONNECTED", [inp, weight_ids[f"classifier.layers.{layer}.weight"],
                                        weight_ids[f"classifier.layers.{layer}.bias"]], name, [1, out_width],
                    ("FullyConnectedOptions", {"FusedActivationFunction": tf.ActivationFunctionType.NONE}))

    def norm(inp, layer, name):
        mean = g.op("MEAN", [inp, axis], name + "_mean", [1, 1], ("ReducerOptions", {"KeepDims": True}))
        centered = g.op("SUB", [inp, mean], name + "_centered", [1, 256])
        square = g.op("MUL", [centered, centered], name + "_square", [1, 256])
        variance = g.op("MEAN", [square, axis], name + "_variance", [1, 1], ("ReducerOptions", {"KeepDims": True}))
        regularized = g.op("ADD", [variance, epsilon], name + "_regularized", [1, 1])
        inverse_std = g.op("RSQRT", [regularized], name + "_inverse_std", [1, 1])
        unit = g.op("MUL", [centered, inverse_std], name + "_unit", [1, 256])
        scaled = g.op("MUL", [unit, weight_ids[f"classifier.layers.{layer}.weight"]], name + "_scaled", [1, 256])
        return g.op("ADD", [scaled, weight_ids[f"classifier.layers.{layer}.bias"]], name, [1, 256])

    def head(inp, name):
        y = g.op("RESHAPE", [inp], name + "_flat", [1, 1536], ("ReshapeOptions", {"NewShape": [1, 1536]}))
        y = linear(y, 1, name + "_dense1", 256)
        y = g.op("RELU", [norm(y, 2, name + "_norm1")], name + "_relu1", [1, 256])
        y = linear(y, 5, name + "_dense2", 256)
        y = g.op("RELU", [norm(y, 6, name + "_norm2")], name + "_relu2", [1, 256])
        return linear(y, 9, name + "_logit", 1)

    current, preceding = head(x, "current"), head(previous, "preceding")
    both = g.op("MINIMUM", [current, preceding], "confirmed_logit", [1, 1])
    calibrated = g.op("ADD", [both, weight_ids["calibration_logit_offset"]], "calibrated_logit", [1, 1])
    score = g.op("LOGISTIC", [calibrated], "score", [1, 1])
    artifact = g.serialize(x, score)
    report = {"source_sha256": source_hash, "target_sha256": hashlib.sha256(artifact).hexdigest(),
            "bytes": len(artifact), "operators": dict(Counter(op[0] for op in g.ops)),
            "input_shape": [1, 16, 96], "output_shape": [1, 1], "dtype": "float32",
            "logit_offset": float(weights["calibration_logit_offset"]), "threshold": 0.5,
            "note": "Classifier export only; full audio frontend and device acoustic parity are not established."}
    files = [(target, artifact)]
    if manifest is not None:
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
        report["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
        files.append((target.with_suffix(".json"), manifest_bytes))
    files.append((report_path, (json.dumps(report, indent=2) + "\n").encode()))
    write_exclusive_files(files)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--display-label", help="Write a sidecar with a label unique among installed/HA-offered models; does not change the spoken phrase")
    p.add_argument("--language", action="append", help="Trained language tag for the sidecar (for example ru); repeat for multiple languages")
    a = p.parse_args()
    report = export(a.source, a.output, a.expected_sha256, display_label=a.display_label, languages=a.language)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
