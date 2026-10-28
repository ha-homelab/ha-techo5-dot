# One-device acceptance

Record observations and timings privately. An unchecked item is pending, not a pass.

- [x] Confirm the selected Dot 2, working pre-existing TWRP and retained NS6574 build 7623.
- [x] Resolve the damaged cache using verified backup metadata; obtain a clean read-only filesystem check.
- [x] Install TECHO5 v1.0.34 in slot a; obtain the installer's healthy-boot verdict and a responding Home Assistant API.
- [x] Pair with Home Assistant securely and assign **Local Russian Home** to both Assist pipeline selectors.
- [x] Confirm the uniquely labelled personal model is selected, the live TFLite hash matches the private candidate, the engine is openWakeWord, the threshold is 0.5 and the secondary wake word is None.
- [x] Verify the bounded per-device rollback inventory and account for old emOS re-corrupting cache if booted again: 14 archive members independently matched source sizes and SHA-256 checksums.
- [x] Disable the three obsolete voice/BT/scanner entries and verify the pilot Dot's saved Lovelace card uses its available Music Assistant/Sendspin player and native voice controls.
- [x] Retire the obsolete controller identity before deleting its three HA entries; preserve a bounded, integrity-checked database/training backup and the other physical Dot's configuration. See the [October 27 record](status.md#october-27-2026--obsolete-controller-identity-retired).
- [x] Update and validate the pilot's household music script and source-device/satellite routes without changing other endpoints or starting playback.
- [x] Test a software reboot: healthy slot a, stable daemon, matching boot-image and personal model/sidecar hashes, retained selection/pipelines, reconnected native player/satellite and joined Sendspin client.
- [x] Apply the signed v1.0.35 update through HA: healthy slot b, previous good slot a retained, official daemon hash matched, personal model and voice settings preserved. See [update details](updates.md).
- [ ] Test a cold boot after disconnecting and reconnecting power; the software reboot does not cover this case.
- [ ] Validate «Привет, Мышка» at normal speaking volume, near the device and from its usual seat. Include quiet-room and television negatives.
- [ ] Check the Action button, physical mute, indicator states and volume controls.
- [ ] Request a device state, an allowed lighting action and household statistics; confirm both spoken results and actual HA state.
- [ ] Measure end-of-question to **audible answer**, including warm and cold requests. Do not substitute model-token or queued-audio timing.
- [ ] Verify that enabled streaming produces early audible speech and that voice interruption stops a playing response.
- [ ] Play music on the approved speaker; check sustained playback, voice interruption, stopping and resuming.
- [x] Confirm Bluetooth proxy visibility without duplicate active entries: HA received two fresh advertisements through the native passive scanner during a 20-second observation after reboot.
- [x] Activate the corrected assistant media-player allowlist after an HA restart, verify both satellites are idle with preserved wake/assistant settings, and remove the former Music Assistant player plus its orphan HA entity/device.
- [x] After the October 27 cleanup and TECHO5 radio recovery, verify the former identity is absent and both physical proxies deliver fresh observations: 12 TECHO5 reports and 4 EchoMuse reports over 45 seconds, excluding cached reports. The TECHO5 parent ESPHome entry/key, scanner identity, saved settings and personal model were preserved. This is outage-recovery acceptance, not evidence of long-term nonrecurrence.
- [ ] Review the documented update/rollback mechanism before enabling updates.
- [ ] Check remaining automation and music-routing references; record unresolved regressions.

Installation checkpoints were recorded on October 26, 2026; registry retirement was recorded on October 27. Keep the other Dot's configuration intact. Expand only after the pilot meets the household's reliability needs.
