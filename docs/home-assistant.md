# Home Assistant integration

## Current connection

The selected Dot runs emOS/EchoMuse and uses the existing EchoMuse Controller deployment. Its working entities, pipeline and dashboard remain in place during preparation.

## Planned connection

TECHO5 advertises an **ESPHome-native API** device. After a successful pilot installation, Home Assistant should discover it under **Settings → Devices & services**. Use the unit's privately supplied API key for pairing; do not publish it or disable encryption to simplify setup. [Upstream integration](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/README.md#L177-L184)

Select the intended Russian Assist pipeline, retaining the existing household-data policy and local conversation backend. Verify speech recognition, Russian synthesis and exposed-entity permissions separately. TECHO5 is the satellite, not a replacement for these services.

Match the new device and media player explicitly before editing the audio dashboard, Music Assistant/Sendspin routing or automations. Entity names and identifiers may change. Remove old entries only after references and rollback needs have been checked.

Verify Bluetooth advertisements through the new proxy before retiring its old entry. Avoid duplicate proxies or two simultaneously active voice paths for one physical Dot. [Acceptance checklist](acceptance.md)

## Features to validate separately

Retain the existing **Local Russian Home** pipeline, local household conversation
agent and female Russian **Baya** speech configuration. Do not move private home
queries to a cloud model as part of the firmware switch. Other existing speech
providers may still have network dependencies; this is not a claim that the whole
pipeline is offline.

The pinned TECHO5 Bluetooth proxy supports passive advertisements, not active
GATT connections. Verify affected BLE integrations before retiring the old proxy.
Upstream advises disabling BLE proxy while playing Bluetooth phone audio because
that combination can stutter. These are separate tests from Wi-Fi music.

Whole-response delivery is the pinned default. Streaming options and interruption
need end-to-end testing; a progress event alone does not prove early audible speech.
Do not assume this migration fixes server-side LLM latency.

Sources: [Bluetooth implementation](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/feature/bluetooth/bluetooth.go),
[voice defaults](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/config/wake.go).
