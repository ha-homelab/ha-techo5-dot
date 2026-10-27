# Wake-word export and selection

The [wake-word guide](../docs/wake-word.md) covers the audited classifier,
dependencies, parity checks and acceptance limits. These tools export an existing
calibrated model; they do not retrain it or install anything on a device.

## Give each model a distinct Home Assistant label

Home Assistant's wake-word picker uses the displayed phrase as its key. TECHO5
`dot-v1.0.34` advertises all installed models, including models with duplicate
phrases. If an old and a personal model both say `Привет, Мышка`, selecting that
label can select the old model. The personal model may even be loaded successfully
while the picker shows no selected word.

The classifier's ID is its filename stem. The sidecar's `wake_word` is its display
label. A label suffix such as `(personal)` does **not** change what you say: the
audio classifier still recognizes its trained phrase.

Export a sidecar with a label distinct from every installed or HA-offered model:

```sh
python training/export_oww_tflite.py \
  --source private/current-model.onnx \
  --output private/personal-current.tflite \
  --expected-sha256 "$SOURCE_SHA256" \
  --display-label 'Привет, Мышка (personal)' \
  --language ru
```

`SOURCE_SHA256` must come from the reviewed source-model receipt. The optional
label and language arguments create `personal-current.json` alongside the model
and export receipt. They leave the TFLite bytes unchanged. All three outputs use
private permissions and exclusive creation: an existing requested output aborts
the export without replacing it. Omitting both arguments retains the original
model-and-receipt workflow. The exporter cannot check labels on a remote device;
check their uniqueness before choosing one.

For a model already exported and validated, update only `wake_word` in its
same-stem sidecar through the normal administrative workflow. Preserve the model
filename, language tags and TFLite bytes. Keep the updated sidecar's checksum in
the private deployment receipt so its metadata remains traceable.

## Check the selection by ID

After installing the model and sidecar through normal administrative access:

1. Reload/restart the daemon and reconnect its HA integration so both reread the
   model library and advertised labels.
2. Choose the unique personal label in the first wake-word slot; choose **No wake
   word** in the second slot if only one trigger is wanted.
3. Confirm the saved `wake.words[0].id` and the daemon's `wake words listening`
   active ID match the personal TFLite filename stem. A label alone is insufficient.
4. Set the calibrated threshold to `0.5` in the device/HA setting. The sidecar's
   `recommended_threshold` documents the recommendation; it does not set it.
5. Wait for the model to finish warming up, then test the actual spoken phrase.
   Successful loading and classifier parity do not establish room acoustics or
   end-to-end voice quality.

Upstream behavior: [model IDs and sidecars](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/lib/wake/models.go),
[phrase-keyed advertisement](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/lib/wake/library.go#L117-L147).
