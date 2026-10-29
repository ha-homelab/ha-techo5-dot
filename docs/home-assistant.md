# Home Assistant integration

## Current connection

Both physical Dots now connect directly through encrypted ESPHome and run **TECHO5 v1.0.39** after the October 28 signed OTA updates. Neither Dot depends on its former EchoMuse Controller record. Dashboard and voice/music routes were reconciled during migration, and both scanners forwarded fresh Bluetooth observations after the updates. See the [update record](updates.md) and [deployment status](status.md) for the exact checks and remaining acoustic acceptance.

Before migration, this Dot used emOS/EchoMuse through EchoMuse Controller. The installer preserved its older EchoLocal name and pairing material and now advertises the physical device's factory network identity. That identity is different from the former controller's virtual identity. Reconcile existing HA entries before treating a discovery as a new physical speaker; do not publish either the identifiers or the encryption key.

The [signed v1.0.35 update](updates.md) preserved pairing, both Assist pipelines and the personal model.

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

## Device administration after migration

A migrated Dot runs TECHO5 Linux and connects directly to HA; its old EchoMuse
Controller console no longer controls it. The USB serial console was verified
on Dot 001 after installation and after a normal software reboot.

For network administration, enable the device's **SSH** switch in HA and use
`ssh root@<dot-address>` with the private key matching the operator public key
installed during migration. The public repository contains no login secrets,
and this deployment does not rely on a shared SSH password. Turn SSH off after
maintenance. In the verified final state, SSH and the remote API are off.

Normal voice and music operation requires power and Wi-Fi, not a USB connection
to Synology. Retain USB data access for recovery or future system migrations.
A saved configuration alone is not an operating-system rollback; see
[migration and recovery](migration.md).

## Entities, dashboard and Bluetooth

Match the physical device and its media player explicitly before editing the audio dashboard, Music Assistant/Sendspin routing or automations. Reused legacy identities can coexist with stale controller entries. Check their references and the intended rollback path before retiring them.

At the October 26 pilot checkpoint, the three old voice/BT/scanner entries were disabled and unloaded without restarting HA. They were initially retained because the shared controller still advertised the old identity. On October 27, the obsolete controller record and those three HA entries were removed after a bounded private backup. See [retiring the former controller identity](#retire-the-former-controller-identity) below.

Only this Dot's Lovelace card was remapped to its available Music Assistant player and six native voice controls. Music Assistant uses this physical Dot's Sendspin output and provides queue and transport controls. The saved dashboard configuration was verified. At the pilot checkpoint, the native TECHO5 proxy remained enabled and its scanner registered after reboot. HA received two fresh advertisements from two distinct devices through it during a 20-second observation, separately from cached reports.

The migration also required updating the household music script and its source-device/satellite routes. They still referred to the old virtual device and an unavailable EchoMuse player even after native pairing succeeded. The pilot now resolves to its available Music Assistant player; configuration validation passed, followed by a scripts/automations reload without restarting HA. Review these mappings separately from the dashboard: changing a card does not change where voice commands send music. This verifies routing configuration, not audible playback.

Verify Bluetooth advertisements through the TECHO5 proxy. Avoid two active proxies or voice paths for one physical Dot. The pinned proxy supports passive advertisements, not active GATT connections. Upstream advises disabling BLE proxy while playing Bluetooth phone audio because that combination can stutter. These are separate tests from Wi-Fi music.

Read each diagnostic sensor's unit and state class before comparing numbers. The current TECHO5 advertisement sensor reports a **rate in advertisements per second** (`/s`); it can legitimately decrease. The EchoMuse advertisement sensor is a **cumulative total** (`total_increasing`). A rate is not a lifetime counter, and a registered scanner alone does not establish reception. Observe fresh HA advertisement events with the intended scanner as their source.

### Retire the former controller identity

A disabled **EchoMuse BT Proxy** card beside the TECHO5 scanner is a retained configuration entry. It is not evidence of another radio or a failed TECHO5 connection. Repeated labels within one integration card also do not count as separate proxies. Conversely, an EchoMuse proxy belonging to the other physical Dot is a legitimate separate scanner.

The controller continues advertising approved devices through mDNS while they are offline, although their TCP listeners are stopped. Deleting only HA's old entry can therefore produce another discovery. Retire the source first:

1. Identify the migrated physical Dot and its old controller record, voice endpoint, BLE endpoint and HA entries. Check entity references in dashboards, scripts, automations and the local assistant's media-player allowlist. Preserve the other Dot's records.
2. Take a small private SQLite **online backup**, including committed WAL data, and preserve any recordings needed for training. Check the backup with SQLite integrity validation and compare copied recording hashes. A full Alexa filesystem backup is unnecessary for this registry operation.
3. Use the controller administrator's delete-device operation for **only the migrated record**. In the verified controller, `DELETE /api/devices/{device_id}` removes its voice and BLE listeners and their mDNS registrations. This is a hard delete: it also removes that record's stored configuration, keys, device logs, boot/wear records, wake samples and ordinary utterance recordings. Saved copies are needed if the old controller enrollment must later be reconstructed. The separate training-recorder directory is outside this deletion path; verify its preservation rather than assuming all audio uses the same storage.
4. Remove the corresponding obsolete ESPHome voice/BLE entries and Bluetooth scanner entry through HA's integration controls. The supported administrator API is `DELETE /api/config/config_entries/entry/{entry_id}`. Do not edit live `.storage` files. Disabling **BLE proxy** alone is insufficient for full retirement: it stops BLE advertising but leaves the old voice advertisement.
5. Confirm the former identity no longer appears in controller discovery, HA entries or active scanners. Verify fresh advertisements from the replacement, its available voice/player entities, and the other Dot's operation independently. Retained historical metrics are not discovery sources.

The October 27 cleanup removed **three obsolete configuration entries, three device records and ten entity records**. The private backup contained an integrity-checked controller database and **56 training files** in an approximately **2.65 MB** compressed archive. Every training file matched the retained source by path, size and SHA-256 after retirement. The other Dot's controller configuration was unchanged. These counts describe this cleanup, not a general deletion target.

The former Music Assistant player was removed separately through its supported player-configuration API; HA removed the resulting orphan entity and empty device automatically. Two outdated local-assistant allowlist references were updated to the current native and Music Assistant players, then activated by restarting HA. Both satellites returned idle with their wake word and assistant selections preserved.

### A registered scanner can still be silent

The October 27 audit also found a separate TECHO5 radio failure: the STP/Bluetooth bridge was unhealthy, and the daemon could not set BLE scan parameters (`EAGAIN`). Voice and API availability did not establish Bluetooth health. A normal operating-system reboot restored the radio path; restarting only the application had not recovered it. No new firmware or wake-word model was installed.

After recovery, a **45-second** HA observation received **12 fresh reports from TECHO5** and **4 from the other physical Dot's EchoMuse proxy**. The observation excluded 42 cached reports. Both satellites remained idle; saved settings, personal model, sidecar and authentication-key hashes were unchanged, and temporary SSH access was switched off again. These measurements verify recovery of this outage, not a permanent fix for the underlying radio problem or a minimum advertisement rate.

During proxy recovery, HA recreated the TECHO5 child Bluetooth configuration entry with the same scanner MAC and source ownership. Its parent ESPHome entry and encryption key were retained. A changed child entry ID alone does not mean a new physical proxy was added.

## Features still requiring audible tests

Enabling streamed replies does not establish that the first audio plays before generation ends. Whole-response delivery is the pinned default; the pilot overrides that setting. Measure end-of-question to **audible speech**, and test interruption while a reply is playing. A progress event or queued audio is not a completed audible response.

Wake recognition, false activations, music continuity and Bluetooth behavior remain part of the [acceptance checklist](acceptance.md). TECHO5 remains a satellite: changing its firmware does not itself remove server-side inference latency.

Sources: [Bluetooth implementation](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/feature/bluetooth/bluetooth.go),
[voice defaults](https://github.com/HuskerMinion/techo5/blob/248b9dafe3dec0ace21604f2b5986f7e52ab41d6/echod/internal/config/wake.go).
