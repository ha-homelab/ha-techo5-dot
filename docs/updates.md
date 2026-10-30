# Firmware updates

If a Dot answers ping but its native HA entities remain unavailable after
repeated boots, follow [rescue-mode diagnosis and recovery](rescue-recovery.md)
before considering another firmware installation.

## October 29, 2026: both Dots updated to v1.0.40

Both native Home Assistant firmware entities offered **v1.0.40**. The updates were installed sequentially from **v1.0.39**, preserving the current personal wake-word and Assist configuration. The release manifest signature was verified before installation; manifest SHA-256: `fed13874c391baa844ac939d21251427b182a9f82042c276f202fa8de1962a0e`.

The [upstream release](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.40) reports a fix for pauses prematurely ending quietly spoken requests. This maintenance does not establish improved acoustic behavior; that needs a separate listening test. The release also renames the alarm actions that take an `id` to `alarm_turn_off_id` and `alarm_turn_on_id`. Check any automation using `alarm_turn_off` or `alarm_turn_on` with an `id` when upgrading. The pre-update scan of 93 deployed HA YAML/custom-sentence/dashboard files found no old alarm-action references; no automation changes were needed within that scope.

Audiocenter initially encountered a GitHub TLS timeout and a download rate near 19.6 kB/s. The device's own recovery re-associated Wi-Fi, detected a two-minute transfer stall and resumed from byte 2,439,551. It then completed the download and entered slot installation. A read-only USB log check confirmed these phases and adequate free space. No manual reboot, parallel install or replacement download was used; low progress alone was not treated as installation failure.

Both devices reconnected after their automatic reboot, reported the expected installed version and an `installed` outcome, and cleared their pending update. Existing settings comparisons covered **112 entities on Dot 001 and 112 on Dot 002, with no changed values**. The personal «Привет, Мышка» selection, threshold, primary streamed replies, both Local Russian Home selectors, microphone configuration, wake tone and access settings were preserved. Automatic future updates remain disabled.

Both native satellites and players were available, and per-scanner Bluetooth observation timestamps advanced on both physical proxies. Music Assistant was being upgraded in a separate coordinated maintenance window: its players were temporarily unavailable and Sendspin was waiting. That external service readback was handed to the HA maintenance owner; music readiness is not claimed by this OTA record. Checks included more than two minutes since each new boot. No microphone capture, spoken request, music playback or household action was triggered. Boot-slot metadata and installed file hashes were not independently checked in this OTA run. Only small configuration/verification receipts and the signed manifest were retained privately; no full firmware or device backup was added.

## October 28, 2026: both Dots updated to v1.0.39

The user requested the two updates offered in Home Assistant. Audiocenter / Dot 001 moved from **v1.0.38 to v1.0.39**, followed by Dot 002 from **v1.0.36 to v1.0.39**, using each native `update.install` action. The second request was sent only after the first unit reconnected, passed configuration and Bluetooth checks, and remained available beyond two minutes after boot. Both updates finished with an `installed` outcome, the expected installed version, no update pending and no update in progress.

The [official release](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.39) adds optional AirPlay volume control and Home Assistant actions to enable or disable alarms without deleting them. AirPlay volume control is off by default; this maintenance did not opt into new features or automatic future updates. The release manifest signature was verified with the previously pinned upstream public key before installation. Its SHA-256 is `b80aadeb663b3f4f789c054deb95a93be103108a3e28b06edb4116d3eaff4133`. Device installation used the existing signed OTA mechanism; no additional firmware archive or full-device backup was retained.

Before/after comparisons covered **111 existing configuration entities on Dot 001 and 111 on Dot 002, with zero changed values**. The personal «Привет, Мышка» selection, threshold 0.5, disabled secondary wake word, both Local Russian Home selectors, streamed primary replies, wake tone, microphone settings, BLE proxy and Sendspin were preserved. SSH, the remote API and wake-clip capture remain off. Newly added controls were not changed.

After both automatic reboots, the native satellites and players were idle, both Music Assistant players were available and both Sendspin clients were joined. Per-scanner HA diagnostic timestamps advanced for both physical Bluetooth proxies. This establishes fresh forwarding during the check, rather than relying only on a registered scanner or the shared advertisement feed.

No spoken command, recording, music playback or home-control action was triggered. Direct boot-slot metadata, deployed binary/model hashes and acoustic behavior were not independently rechecked during this OTA maintenance. Private receipts retain the signed manifest, requested/offered versions, update progress, reboot timestamps, settings comparisons and scanner observations.

## October 26, 2026: v1.0.34 to v1.0.35

The active Dot 2 was updated using its native Home Assistant firmware entity. The initial installation remains documented against v1.0.34 in [upstream-lock.json](../upstream-lock.json); that lock also identifies the original classifier-parity baseline. The deployed platform release at that checkpoint was [dot-v1.0.35](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.35), commit [`b026039c75777197fdb901b8b1a1c55a8c7ed80c`](https://github.com/HuskerMinion/techo5-dot/tree/b026039c75777197fdb901b8b1a1c55a8c7ed80c).

### Changes relevant to this Dot

- Wake-word readiness and utterance state are reset when muting, so stale state is not reused after unmute. [Upstream change 301](https://github.com/HuskerMinion/techo5/pull/301)
- Microphone history and the live stream join at the same capture boundary, preventing duplicated or missing frames at that boundary. [Upstream change 302](https://github.com/HuskerMinion/techo5/pull/302)
- Home Assistant gains a Visit link to the device's setup page. The release also adds AirPlay 2 to Dot 3; that is a different board from this pilot.

The Dot 2 kernel and rescue-package digests are unchanged from v1.0.34. These microphone fixes do not establish better acoustic sensitivity or lower end-to-end latency; those still require listening tests.

### Update procedure and verification

1. Confirm the intended device, installed version and offered release in HA. Check that it is not playing audio or handling a voice request.
2. Review the release and verify its signed manifest. Preserve current settings privately. This pilot uses TECHO5's existing update mechanism and A/B storage; it does not repeat the initial OS migration.
3. Install the offered firmware from the device's HA update entity. Allow the device to restart and reconnect. An accepted request or 99% progress is not completion.
4. Confirm the installed version, loaded model, preserved settings and boot-health result. The update writes the other root-filesystem slot and keeps the prior good slot.
5. Test audible behavior separately. Automatic future updates need a separate decision; they remain disabled for this pilot.

For this update, the signed manifest SHA-256 is `e7b247684ca98cfafa804cab7916102b554c78e74e072c42537fb06756578cbf`; the installed `echod-arm-dot` SHA-256 is `285d51a26bb5875721520fbabd4729d2b1e9cc80e1ddd7a2857577346b748059`, matching the official release. Private receipts retain the before/after settings and personal-file digests.

The personal OWW model loads under **«Привет, Мышка (personal)»**, with threshold **0.5** and the secondary wake word disabled. Both pipelines remain **Local Russian Home**. HA reconnects, the native satellite and players are idle, Sendspin is joined, and BLE proxy, streamed replies and the wake tone retain their settings. SSH and automatic updates remain off.

At approximately 102 seconds after reboot, slot b was marked **good**, the boot-attempt counter was **0 healthy**, and the daemon remained running. Slot a retained the previous good v1.0.34 system. The persisted wake-word, microphone and Bluetooth configuration sections were unchanged.

Voice recognition, music quality and acoustic latency were not tested during this update, at the user's request. The earlier numerical classifier-parity result is not a new full-pipeline test of v1.0.35. See [acceptance](acceptance.md) for the remaining checks.
