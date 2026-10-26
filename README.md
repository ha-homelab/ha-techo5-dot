# HA · TECHO5 Dot

**A prepared pilot for bringing an existing Echo Dot 2 into Home Assistant through TECHO5. No device has been migrated.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

This repository records compatibility decisions, private preparation and acceptance checks. It does not replace upstream firmware or contain device credentials, recordings, model weights or unlocking tools.

![Current EchoMuse connection and planned TECHO5 connection](docs/assets/architecture.svg)

## Where we are

One Dot is online on **EchoMuse/emOS**; the other is offline. USB maintenance access is unavailable, so this stage prepares files and documentation only. Home Assistant, firmware and voice settings remain unchanged. See the dated [status](docs/status.md).

The evaluation target is [TECHO5 Dot v1.0.34](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.34), pinned to [`88b2670`](https://github.com/HuskerMinion/techo5-dot/tree/88b26703d5e1a97d5ce0fee90805e8a3dd206a95). Newer `main` is not the pilot baseline. See [upstream-lock.json](upstream-lock.json) for exact source pins.

## Why evaluate it?

TECHO5 combines direct ESPHome-native Home Assistant connectivity, seven-microphone averaging, Bluetooth audio/proxy, Sendspin and signed updates with A/B rollback. These are upstream capabilities to verify on our hardware, not completed local results. It still uses Home Assistant's speech and conversation services; changing satellite firmware does not eliminate slow server-side inference.

The author reports three Dot 2 units in daily use. That supports a **single-device trial**, not immediate replacement of both working configurations. [Upstream status](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/README.md#L62-L65)

## Follow the preparation path

1. Check [device compatibility and migration boundaries](docs/migration.md).
2. Prepare [the custom wake word](docs/wake-word.md); the current ONNX model is not a drop-in microWakeWord model.
3. Review [Home Assistant integration](docs/home-assistant.md).
4. Complete [acceptance checks](docs/acceptance.md) before expanding the pilot.

Read [SECURITY.md](SECURITY.md) before handling private material and [THIRD_PARTY.md](THIRD_PARTY.md) for upstream attribution. This is an independent homelab project, not an Amazon or TECHO5 endorsement.

## Local verification

Python 3.11+ can run the standard-library checks:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
python3 scripts/check_public.py --include-untracked
```

Verify a downloaded official asset without executing it:

```sh
python3 scripts/verify_assets.py private/releases/dot-v1.0.34/echod-arm-dot
```

Personalized model conversion has separate optional dependencies and regression
checks described in the [wake-word guide](docs/wake-word.md).

Repository creation and shared CI policy are described in [repository governance](docs/repository-governance.md).
