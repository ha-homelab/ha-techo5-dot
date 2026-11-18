# Documentation

Operating notes for running TECHO5 firmware on second-generation Echo Dot units
in Home Assistant, from firmware and wake word through recovery.

## Firmware and upgrades

- [Pilot status](status.md) — the current beta target and where the pilot stands.
- [Myshka signed firmware updates](signed-ota.md) — the supported hardware and how updates are signed.
- [TECHO5 v1.0.49 update review](upstream-1.0.49.md) — what the beta target incorporates.
- [Firmware updates](updates.md) — what to check when a Dot pings but its entities are unavailable.
- [emOS cache filesystem recovery](emOS-cache-recovery.md) — the repaired cache filesystem and its read-only check.

## Features

- [Home Assistant integration](home-assistant.md) — the encrypted ESPHome connection and current version.
- [Native SIP phone](phone.md) — using the `echod` speakerphone with the Home Assistant integration.
- [Bringing the Russian wake word](wake-word.md) — the phrase in use and the private model behind it.
- [Making a TECHO5 Dot useful beyond voice](capabilities.md) — the capability audit of the pilot device.
- [Administration and local media receivers](capability-access.md) — extending the audit to admin and local receiving.
- [Additional Home Assistant controls](capability-package.md) — the capability package shipped as controls.
- [Additional capabilities: deployment and verification](capability-deployment.md) — the October 2026 expansion and how it was verified.

## Announcements

- [Announcements over music — beta 1](guarded-announcement-ducking.md) — the opt-in music-ducking mode.
- [Guarded announcement validation — 2026-10-29](guarded-announcement-validation.md) — the experimental daemon and its build.

## Recovery and acceptance

- [Recovering a Dot that remains in rescue mode](rescue-recovery.md) — starting from the symptom that ping replies but entities are gone.
- [Per-device acceptance](acceptance.md) — recording observations privately, and why unchecked is not a pass.
- [Compatibility and migration](migration.md) — the pilot device identity and the other supported models.
- [Repository governance and publication](repository-governance.md) — how the public repository is provisioned.
