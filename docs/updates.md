# Firmware updates

## October 26, 2026: v1.0.34 to v1.0.35

The active Dot 2 was updated using its native Home Assistant firmware entity. The initial installation remains documented against v1.0.34 in [upstream-lock.json](../upstream-lock.json); that lock also identifies the original classifier-parity baseline. The current deployed platform release is [dot-v1.0.35](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.35), commit [`b026039c75777197fdb901b8b1a1c55a8c7ed80c`](https://github.com/HuskerMinion/techo5-dot/tree/b026039c75777197fdb901b8b1a1c55a8c7ed80c).

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
