# Pilot status

## October 26, 2026 — signed update to v1.0.35

The active Dot was updated through Home Assistant to **TECHO5 v1.0.35, slot b**. The release manifest signature and hashes were verified. The installed daemon matches the official binary digest; the personal model and its sidecar retain their previous hashes. Home Assistant reports the current version, no update in progress and unchanged voice, BLE and Sendspin settings. Slot b was committed as good with a healthy boot counter; the previous good v1.0.34 remains in slot a. Automatic future updates remain disabled.

See the [update record](updates.md) for release changes and verification. Voice and music listening tests remain postponed at the user's request.

## October 26, 2026 — initial installation and pairing

One Echo Dot 2 was initially installed with **TECHO5 v1.0.34, slot a**. The installer completed successfully, reported a healthy boot, and the Home Assistant API answered. Native encrypted ESPHome pairing succeeded. The other Dot remains offline and unchanged.

- Both Assist pipeline selectors use **Local Russian Home**, preserving the household conversation policy.
- The personal OWW TFLite model is selected and loaded in the openWakeWord engine; its live SHA-256 matches the private candidate. The unique selector label is **«Привет, Мышка (personal)»**; the spoken phrase remains **«Привет, Мышка»**. A duplicate label initially selected an older microWakeWord model. The corrected model ID and runtime were checked together.
- The verified threshold is **0.5**, with the secondary wake word set to **None**.
- BLE proxy and streamed replies are enabled. After reboot, HA received two fresh advertisements from two distinct devices through this Dot during a 20-second observation. This verifies passive reception, not active GATT connections. Audible streaming still requires acceptance.
- The three obsolete voice/BT/scanner entries for this Dot were disabled and unloaded without restarting HA. Its Lovelace card now uses the available Music Assistant player, backed by this Dot's Sendspin output, and six native voice controls. The saved configuration was verified. The other Dot's card was not changed.
- The household music script and source-device/satellite routes now target this Dot's available Music Assistant player. Configuration validation passed; only scripts and automations were reloaded. No music was played during this routing check.
- A software reboot passed: a new kernel boot ID, healthy slot a and a stable daemon process were confirmed after approximately 103 seconds. The saved and installed boot-image hashes matched. Personal TFLite and sidecar hashes, the selected ID, threshold and empty secondary slot were preserved. HA reconnected with its native player/satellite idle, and the Sendspin client joined. A power-disconnect cold boot has not been tested.
- Near/far wake recognition, quiet-room and television negatives, spoken commands, audible latency and sustained music playback remain unverified on TECHO5.

The retained system was confirmed as **NS6574 build 7623**, with working pre-existing TWRP. A damaged cache filesystem initially blocked preflight. Standard metadata repair with a surviving backup superblock and a **48 KiB** undo file succeeded; a separate read-only filesystem check returned **exit code 0**. No blind cache format or userdata wipe was used. [Recovery record](emOS-cache-recovery.md)

The bounded recovery archive contains 13 boot-critical originals plus the generated TECHO5 image, approximately **50 MiB compressed**. All 14 archive members independently matched their source sizes and SHA-256 checksums. The archive is stored privately on the Mac with file mode `0600`; no full Alexa disk archive was recreated. Returning to the old emOS image still carries the documented cache-corruption risk.

The pinned platform remains [`88b26703d5e1a97d5ce0fee90805e8a3dd206a95`](https://github.com/HuskerMinion/techo5-dot/tree/88b26703d5e1a97d5ce0fee90805e8a3dd206a95), with daemon [`248b9dafe3dec0ace21604f2b5986f7e52ab41d6`](https://github.com/HuskerMinion/techo5/tree/248b9dafe3dec0ace21604f2b5986f7e52ab41d6). Newer upstream releases are not the pilot baseline. See [upstream-lock.json](../upstream-lock.json).

Next: complete the remaining end-to-end [acceptance checks](acceptance.md), including audible music playback, actual wake recognition and spoken replies. [Migration](migration.md) · [Wake word](wake-word.md) · [Home Assistant](home-assistant.md)

## October 25, 2026 — preparation history

At this earlier checkpoint, one Dot was reachable through EchoMuse and the other was offline. USB maintenance access was unavailable. No firmware, Home Assistant integration or live voice settings changed during that preparation stage.

The private configuration and existing Russian wake-word source were preserved. An OWW TFLite candidate passed classifier regression checks against the ONNX source. That established conversion parity, not recognition quality on the new device frontend. The microWakeWord web upload is not the correct route for this model.

Seven official release assets were staged in ignored local storage and passed size/SHA-256 checks against the release metadata. This verified downloaded bytes, not device compatibility or installation success.

Old full Alexa partition backups were deliberately removed. They are not available recovery evidence and were not recreated. The migration instead retains a bounded per-device recovery set. A saved configuration alone restores settings, not an operating system.
