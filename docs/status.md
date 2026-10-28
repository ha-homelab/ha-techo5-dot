# Pilot status

## October 28, 2026 — both physical Dots migrated

The remaining EchoMuse unit, **Dot 001 / Audiocenter**, now runs **TECHO5 v1.0.38 in slot a**. Dot 002 remains on **v1.0.36**; its firmware, native HA entry, pairing data and voice selections were preserved. The installer source was pinned to [`e369da6fb320c79d027acf25acfab7c4ab8c4cd9`](https://github.com/HuskerMinion/techo5-dot/tree/e369da6fb320c79d027acf25acfab7c4ab8c4cd9), and the release manifest signature and asset hashes were verified. This is a separate deployment record; the original v1.0.34 pilot lock remains historical.

The USB serial identity, existing TWRP and retained NS6574/7623 system were verified before installation. This unit also had the emOS cache-superblock damage described in the [recovery record](emOS-cache-recovery.md). Three surviving metadata copies agreed. Standard filesystem repair with a 48 KiB undo file was followed by a clean read-only check. No cache format or userdata wipe was performed.

The per-device recovery archive is approximately **51.8 MB compressed**. All 14 saved image files independently matched their source sizes and SHA-256 hashes. The installer wrote and read back the generated boot image; its first boot was healthy. A subsequent normal software reboot also reached a healthy slot a, with the official daemon hash and personal-model hashes matching. Slot b is still empty on this newly installed unit; the initial migration is not protected by an older TECHO5 slot.

The personal **«Привет, Мышка (personal)»** model remains the sole selected wake word at threshold **0.5**. Both Assist selectors use **Local Russian Home**, streamed replies and the wake tone are configured, and training/utterance capture remains off. Encrypted ESPHome pairing, the native player and the Music Assistant Sendspin player are available. SSH and the remote API remain off. These checks do not establish audible recognition or playback quality.

The Audiocenter card, household command routes, family-activity music mapping and assistant media-player allowlist now use the native TECHO5 and current Music Assistant identities. The old controller record, three HA voice/BLE/scanner entries and old Music Assistant player were retired. The bounded controller backup passed SQLite integrity validation; all **56 training files** matched after retirement. HA returned to running after a normal restart, with the shared Assist pipeline file unchanged.

Per-scanner Home Assistant diagnostics confirmed **Dot 001: refreshed observations from 10 distinct devices over 11.39 seconds, Dot 002: refreshed observations from 35 distinct devices over 11.39 seconds**; both scanners' last-detection timestamps advanced. There are two loaded scanner entries, one per physical Dot. The shared 45-second advertisement feed reported 36 fresh events for Dot 002 and none for Dot 001, while the latter's own radio received 23 advertising reports in an 8-second trace. Per-scanner HA timestamps resolve that misleading shared-feed result: a zero count in the shared feed alone is not proof of a silent proxy. These checks establish fresh forwarding during the observation, not long-term radio reliability or active GATT connections.

No microphone recording, music playback, spoken response or physical home-control action was triggered by these maintenance checks. Physical cold-boot and room-distance voice/music acceptance remain user tests. Later offered firmware releases were not silently installed during this pinned migration.

## October 27, 2026 — obsolete controller identity retired

The migrated Dot's former EchoMuse controller record was still approved and advertised through mDNS while offline. Its disabled Bluetooth entry therefore remained visible beside the active TECHO5 scanner. HA confirmed the migrated device was running **TECHO5 v1.0.36**; no firmware update was performed during this repair. The other physical Dot was online through EchoMuse and was preserved.

After a bounded private backup, the old controller record was removed through its administrator API, followed by its three obsolete HA voice/BLE/scanner entries. HA removed three old device records and ten entity records. The backup was approximately 2.65 MB compressed and included an integrity-checked SQLite online backup plus 56 training files; no full Alexa filesystem archive was created. The other Dot's controller configuration was unchanged, and the active HA entries remained loaded.

Two stale media-player allowlist references in the local assistant configuration were also replaced with the migrated Dot's current native and Music Assistant players. These changes are active after an HA restart: HA reports running, both satellites are idle, and the wake word and both assistant selectors are preserved. The old Music Assistant player was removed through its supported player-configuration API; HA then removed its orphan entity and empty device automatically. This is separate from the three-entry cleanup above.

The other physical Dot's separate encrypted EchoMuse BLE endpoint was enrolled in HA. It connected and subscribed successfully. The TECHO5 device also had a distinct STP/Bluetooth bridge failure that prevented scanning despite its registered proxy; a normal operating-system reboot restored reception. No firmware or wake-word model was changed.

Final verification received **12 fresh TECHO5 advertisement reports and 4 fresh EchoMuse reports in 45 seconds**, excluding 42 cached reports. Both satellites were idle. Saved settings, personal-model, sidecar and authentication-key hashes were unchanged; temporary SSH access was disabled again. HA recreated the TECHO5 child Bluetooth entry with the same scanner identity and source ownership while preserving its parent ESPHome entry and encryption key. The native TECHO5 diagnostic is an advertisement **rate** (`/s`); the EchoMuse sensor is a cumulative total.

HA finished running with **exactly two loaded Bluetooth entries, one per physical Dot**. The three old entries and former Music Assistant wrapper were absent, with no pending ESPHome setup flows or related repairs. Protected Assist pipeline, household and family configuration files were unchanged. The assistant media-player allowlist was updated in its separate configuration file as described above.

This confirms recovery of the observed outage. Long-term nonrecurrence of the radio failure has not been established, and no minimum advertisement rate or audible voice/music result is implied. See the [retirement procedure](home-assistant.md#retire-the-former-controller-identity) for stale-entry prevention and [scanner recovery](home-assistant.md#a-registered-scanner-can-still-be-silent) for the separate radio issue.

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
