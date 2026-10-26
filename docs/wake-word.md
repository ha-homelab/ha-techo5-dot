# Bringing the Russian wake word to TECHO5

Our existing phrase is **«Привет, Мышка»**. The private EchoMuse model uses
openWakeWord embeddings and an ONNX classifier. TECHO5 can run openWakeWord too,
but its on-device classifier format is **TFLite**. Changing the file extension is
not a conversion.

**October 26 deployment checkpoint:** the converted personal model is selected on
the pilot Dot and loaded in the openWakeWord engine. Its live file hash matches the
private candidate. The unique selector label is **«Привет, Мышка (personal)»**;
the spoken phrase is still **«Привет, Мышка»**. The verified threshold is **0.5**,
with the secondary wake word set to **None**. A software reboot preserved the
model and sidecar hashes, selection and threshold; the openWakeWord engine reported
ready again. Loading the model does not establish near/far recognition or
false-wake performance. See [pilot status](status.md) and [acceptance](acceptance.md).

The tools in `training/` preserve this particular classifier without retraining.
They are deliberately specific to the reviewed architecture: two shared-weight
256-unit dense/LayerNorm/ReLU branches, a shifted embedding view, minimum-of-logits
confirmation and a calibrated final sigmoid. They are not a general ONNX converter.
The exporter checks graph wiring, shapes, finite weights and the supplied source
hash before producing anything.

## What has been demonstrated

An offline conversion regression on 25 October 2026 compared the original private
ONNX with the converted head in the unmodified TECHO5 release interpreter:

- 8,474 embedding windows, including every available owner validation clip:
  24 positive and 32 negative clips.
- 64 synthetic positive and 64 synthetic negative validation clips, plus
  512 sampled background windows and 25 numerical stress controls.
- Zero decision differences at threshold **0.5**.
- Maximum absolute score difference **0.00000166893**, below the declared
  tolerance of **0.00001**.

The [aggregate receipt](../training/results/classifier-parity-20261025.json)
contains no recordings, embeddings, household identities or model weights.
Numerical stress controls are arbitrary embedding vectors; they are not recordings
of silence and are not a false-wake test.

This establishes **classifier conversion parity**, not improved recognition.
The samples already participated in development/validation. They are not a fresh
independent acoustic test. TECHO5's complete audio frontend, sustained performance
on the Dot and recognition across the room remain separate checks. The successful
interpreter comparison ran on a macOS ARM64 host, not a Dot's ARMv7 processor.

The tooling was revalidated with [ONNX 1.22.0](https://pypi.org/project/onnx/1.22.0/)
in a separate environment after updating the dependency pin. All nine synthetic
tests passed; the private model exported to identical TFLite bytes, and the
8,474-window comparison retained the same error and zero changed decisions.

On October 26, the expanded suite passed **all 12 training tests** with the
compiled pinned interpreter configured, including the actual runtime parity test
rather than a skip. The 12 repository source tests also passed. These checks
validate conversion and tooling behavior, not acoustic acceptance.

## Small dependency setup

Reuse a suitable Python environment, or create one inside the ignored `private/`
directory. Python 3.11 with ONNX 1.22.0 is tested. TensorFlow, training datasets and a
new training environment are not required.

```sh
mkdir -p private
python3 -m venv private/wake-env
. private/wake-env/bin/activate
python -m pip install -r training/requirements-verify.txt
```

The exporter needs NumPy, ONNX, FlatBuffers and the small `tflite` schema package.
The verifier also uses ONNX Runtime. Go 1.25 or newer builds the parity harness.
The pinned interpreter includes a small vector-kernel package; no Go modules need
to be downloaded.

## Obtain the exact interpreter and run synthetic tests

The fetcher downloads only reviewed source files and their license, pinned by
commit, byte size and SHA-256 in
[`upstream-runtime-lock.json`](../training/upstream-runtime-lock.json). It does
not download firmware, executable binaries, models or datasets, and does not
execute downloaded source. The destination must not already exist.

```sh
python training/fetch_runtime.py --destination private/techo5-runtime
(cd private/techo5-runtime && GOTOOLCHAIN=local GOPROXY=off go build -o ../wakeparity .)
TECHO5_PARITY_RUNTIME="$PWD/private/wakeparity" \
  python -m unittest discover -s training/tests -v
```

The tests create synthetic weights and inputs in temporary directories. They check
the real exported TFLite against ONNX Runtime, including positive and negative
decisions and a case that distinguishes two-view confirmation from a single view.
They also exercise wrong hashes, altered shift semantics, non-finite weights and
reference outputs, private output permissions and overwrite protection.

Without `TECHO5_PARITY_RUNTIME`, the graph/exporter/guard tests still run, but the
actual interpreter parity test is explicitly skipped. CI intended to verify
portability should set the variable and run the complete command above.

## Export the preserved private model

First obtain the expected SHA-256 from the verified deployment or model receipt.
Do not treat an arbitrary file as trusted merely by computing a new expected hash
from it. Set `SOURCE_SHA256` to that reviewed value:

```sh
python training/export_oww_tflite.py \
  --source private/current-model.onnx \
  --output private/current-model.tflite \
  --expected-sha256 "$SOURCE_SHA256" \
  --display-label 'Привет, Мышка (personal)' \
  --language ru
```

The model, its `.export.json` receipt and same-stem `.json` sidecar are created
with permissions `0600` and an output umask of `077`. Existing outputs are never
overwritten. The label must be unique among installed and HA-offered models; it
does not alter the spoken phrase or the TFLite bytes. See the
[export and selection notes](../training/README.md).
The conversion stays float32. It preserves the shifted view, the minimum operation
and the original calibration offset. It uses `STRIDED_SLICE`, `PACK` and `RESHAPE`
because this release's interpreter does not implement `CONCATENATION`, even though
its schema declares that opcode.

The model input is `[1, 16, 96]`, output `[1, 1]`, and the calibrated decision
threshold is **0.5**. The old uncalibrated threshold must not be applied again.

## Compare against existing private embeddings

`--work` points to an existing preparation directory containing `sources.json`,
`features-val/<id>.npz` and `negative-validation.npy`. This tool neither generates
audio nor trains a model. It checks all owner validation clips and bounded subsets
of synthetic/background data. Default limits reproduce the selection policy above.

```sh
python training/verify_oww_tflite.py \
  --work /path/to/existing/private/features \
  --onnx private/current-model.onnx \
  --tflite private/current-model.tflite \
  --runtime private/wakeparity \
  --report private/current-model-parity.json
```

The verifier refuses an existing report, invalid sample counts, too-short
background data, non-finite inputs or reference outputs, and more than 50,000
selected windows. A pass requires both the absolute-error limit and zero changed
decisions. The report records the source hashes and selection digest privately.

## Load through the local model library after the device installation is validated

The release audited here is `dot-v1.0.34`; its daemon source is pinned to
[`248b9dafe3dec0ace21604f2b5986f7e52ab41d6`](https://github.com/HuskerMinion/techo5/tree/248b9dafe3dec0ace21604f2b5986f7e52ab41d6).
The model library recognizes OWW by its 96-wide input shape:
[`models.go:108–150`](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/lib/wake/models.go#L108-L150).

After normal administrative access and the device baseline have been validated,
place the TFLite and matching same-stem JSON in
`/data/misc/echolocal/models/`. This is the Dot build's persistent model-library
directory, not a firmware partition. For example, `current-model.json` contains:

```json
{
  "type": "openwakeword",
  "wake_word": "Привет, Мышка (personal)",
  "model": "current-model.tflite",
  "trained_languages": ["ru"],
  "version": 1,
  "recommended_threshold": 0.5
}
```

Use a plain ASCII filename stem. Arrange the normal controlled daemon
restart/reload, select the phrase in the appropriate HA wake-word slot, and set
the actual slot threshold to **0.5**. The sidecar's recommendation does not set
the runtime threshold. Verify the loaded file hash, selected phrase and threshold.
Keep the custom model selected and review cache-purge behavior before purging
unselected models.

### Avoid duplicate selector labels

The pilot exposed a label collision: the personal OWW model and an older
microWakeWord model were both presented as «Привет, Мышка». The personal model
loaded successfully, but selecting that phrase through HA switched to the older
model. This was a selection problem, not evidence that the OWW model was unsupported.

Give the personal library entry the unique display label
**«Привет, Мышка (personal)»**. This changes the UI label, not the acoustic phrase.
Then confirm all of the following together:

- HA selected the intended unique option.
- The persisted model ID points to the personal library entry.
- Runtime logs report that model ID with **openWakeWord** ready.
- The live TFLite hash matches the private export receipt.
- The actual threshold is **0.5**, the secondary slot is **None**, and these
  settings survive an ordinary reboot.

Keep model IDs and hashes in the private receipt. Do not infer model identity from
the displayed phrase alone or mark acoustic acceptance complete from a load log.

**The web custom-model upload is not this path.** In this release it validates
microWakeWord models, expects `type: micro`, and limits a file to 1 MiB. Our OWW
head is about 1.85 MB. Do not relabel it as microWakeWord or try to evade validation.
See [`own.go:25–86`](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/lib/wake/own.go#L25-L86).

## Remaining acceptance and fallback

Keep the same HA conversation agent and Baya voice while comparing satellites.
Check the complete audio frontend, idle false activations, near/far speech and
recognition during playback on one device before extending the trial. Existing
owner recordings and checkpoints remain private and are not replaced by a stock
English phrase.

TECHO5 also offers HA-side wake detection, which could reuse an ONNX model server
side. Continuous mode streams idle microphone audio to HA; near-miss confirmation
does not check high-confidence local wakes. Those modes change the system's data
flow and are explicit alternatives, not a silent fallback for a failed conversion.
