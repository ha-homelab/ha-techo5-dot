# Home Assistant integration

## Current connection

The selected Dot runs **TECHO5 v1.0.34** and is paired directly with Home Assistant through its **encrypted ESPHome-native API**. Pairing and both Assist pipeline selections were verified on October 26, 2026. The other Dot remains offline and unchanged. See [pilot status](status.md) for the distinction between installation and end-to-end acceptance.

Before migration, this Dot used emOS/EchoMuse through EchoMuse Controller. The installer preserved its older EchoLocal name and pairing material and now advertises the physical device's factory network identity. That identity is different from the former controller's virtual identity. Reconcile existing HA entries before treating a discovery as a new physical speaker; do not publish either the identifiers or the encryption key.

## Pairing and settings

For a new deployment, look under **Settings → Devices & services** for the ESPHome discovery. Use the unit's privately supplied API encryption key; do not disable encryption to simplify setup. [Upstream integration](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/README.md#L177-L184)

The verified pilot configuration is:

- Both Assist pipeline selectors: **Local Russian Home**.
- Primary wake word: **«Привет, Мышка (personal)»**, the unique label for the personal OWW TFLite model; say **«Привет, Мышка»**.
- Primary threshold: **0.5**; secondary wake word: **None**.
- BLE proxy: enabled.
- Streamed replies: enabled.

The personal model ID, openWakeWord load/ready logs and live TFLite hash were checked together. A software reboot preserved the model, sidecar, selected ID, threshold, empty secondary slot and both pipelines. The native player and satellite reconnected, and the Sendspin client joined. A duplicate wake-word label initially made HA select an older microWakeWord model; the unique label resolves that ambiguity. A selector's displayed phrase alone is insufficient. See [wake-word validation](wake-word.md).

Retain the existing **Local Russian Home** pipeline, local household conversation
agent and female Russian **Baya** speech configuration. Do not move private home
queries to a cloud model as part of the firmware switch. Other existing speech
providers may still have network dependencies; this is not a claim that the whole
pipeline is offline.

## Entities, dashboard and Bluetooth

Match the physical device and its media player explicitly before editing the audio dashboard, Music Assistant/Sendspin routing or automations. Reused legacy identities can coexist with stale controller entries. Check their references and the intended rollback path before retiring them.

For the pilot, the three old voice/BT/scanner entries were disabled and unloaded without restarting HA; they were not deleted, avoiding rediscovery from the retained shared controller. Only this Dot's Lovelace card was remapped to its available Music Assistant player and six native voice controls. Music Assistant uses this physical Dot's Sendspin output and provides queue and transport controls. The saved dashboard configuration was verified. The native TECHO5 proxy remains enabled and its scanner registered after reboot. HA received two fresh advertisements from two distinct devices through it during a 20-second observation, separately from cached reports.

The migration also required updating the household music script and its source-device/satellite routes. They still referred to the old virtual device and an unavailable EchoMuse player even after native pairing succeeded. The pilot now resolves to its available Music Assistant player; configuration validation passed, followed by a scripts/automations reload without restarting HA. Review these mappings separately from the dashboard: changing a card does not change where voice commands send music. This verifies routing configuration, not audible playback.

Verify Bluetooth advertisements through the TECHO5 proxy. Avoid two active proxies or voice paths for one physical Dot. The pinned proxy supports passive advertisements, not active GATT connections. Upstream advises disabling BLE proxy while playing Bluetooth phone audio because that combination can stutter. These are separate tests from Wi-Fi music.

## Features still requiring audible tests

Enabling streamed replies does not establish that the first audio plays before generation ends. Whole-response delivery is the pinned default; the pilot overrides that setting. Measure end-of-question to **audible speech**, and test interruption while a reply is playing. A progress event or queued audio is not a completed audible response.

Wake recognition, false activations, music continuity and Bluetooth behavior remain part of the [acceptance checklist](acceptance.md). TECHO5 remains a satellite: changing its firmware does not itself remove server-side inference latency.

Sources: [Bluetooth implementation](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/feature/bluetooth/bluetooth.go),
[voice defaults](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/config/wake.go).
