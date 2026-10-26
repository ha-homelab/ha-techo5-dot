# Pilot status

**2026-10-25 — prepared, not deployed.**

- One existing Echo Dot 2 is reachable through EchoMuse; the second is offline.
- The current configuration is saved privately. Its configured Russian wake phrase is «Привет, Мышка».
- There is no USB maintenance connection to the selected Dot. No firmware, Home Assistant integration or live voice configuration was changed for this preparation.
- The target is `dot-v1.0.34`, released October 25, 2026, at commit `88b26703d5e1a97d5ce0fee90805e8a3dd206a95`.
- The current wake-word artifact uses ONNX. An OWW TFLite candidate passed classifier regression checks; full frontend and device acceptance remain pending. The microWakeWord web upload is not the correct route for this model.

Next: establish the supported maintenance environment, confirm method-specific recovery material, complete wake-word preparation, then run a one-device pilot. [Migration](migration.md) · [Wake word](wake-word.md) · [Acceptance](acceptance.md)

Old full Alexa partition backups were deliberately removed. They are not available recovery evidence. A saved configuration restores settings, not an operating system.

Seven official release assets were staged in ignored local storage and passed size/SHA-256 checks against the release metadata. This verifies downloaded bytes, not device compatibility or an installation.
