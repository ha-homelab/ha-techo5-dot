# Recovering a Dot that remains in rescue mode

A Dot can answer a network ping while its Home Assistant entities remain
unavailable. TECHO5's rescue environment has its own network and USB console;
that does not mean the normal voice service is running.

## What happened on October 29, 2026

After a previously successful v1.0.40 update, Dot 001 became unavailable. Its
USB console identified the rescue environment rather than the normal slot.
The boot record reported five consecutive boots without a healthy checkpoint.
Both slots were still marked `good`: slot a contained v1.0.40 and slot b
contained v1.0.39. The v1.0.40 daemon matched the official release digest, and
the personal wake-word model and sidecar were present.

The counter explains why subsequent power cycles stayed in rescue. It does
not identify what interrupted the earlier boots. There was no retained kernel
crash record available to establish a kernel failure, and no evidence sufficient
to attribute the resets to the power cable or the firmware update.

One use of the supplied retry command returned the unit to slot a on v1.0.40.
The same daemon process remained running and the boot counter became
`0 healthy` at approximately 111 seconds of uptime. Home Assistant's native
satellite and speaker returned, and Music Assistant's Sendspin client rejoined.
Both Bluetooth scanners forwarded fresh observations: 13 devices through the
recovered Dot and 12 through the other Dot during a 14.31-second observation.

On reconnection, HA initially displayed an empty primary wake-word selection
even though the device reported the personal model as active. Reselecting
**Привет, Мышка (personal)** through HA restored the displayed selection. All
112 exposed configuration values then matched the pre-update baseline. The
personal model, sidecar and pairing-key hashes were unchanged. The state JSON
was rewritten by that explicit selection, so byte-for-byte configuration-file
identity is not claimed after it. Normal SSH remained disabled.

No firmware was reinstalled, no Home Assistant restart was needed, and no audio
recording or test call was made. Spoken recognition and audible playback remain
separate acceptance checks; this recovery does not establish why the earlier
boots were interrupted or guarantee that the underlying interruption cannot
recur.

## Diagnose before retrying

1. Connect the intended Dot to a USB host with a data cable. Identify its USB
   serial before opening the console; do not select a device only by an old IP
   address or its position in a USB list.
2. Read the current boot record, slot status, process list and bounded logs.
   Check storage space and filesystem errors. In rescue, `slotctl -s
   /store/techo5 status` shows the stored slots; in the normal system,
   `slotctl status` also identifies the running slot.
3. Preserve small private diagnostic receipts and hashes of configuration,
   pairing data and personal models. Do not publish those files or recreate a
   full Alexa partition backup for this procedure.
4. Confirm that a usable slot exists. A missing slot, a digest mismatch or
   filesystem errors need diagnosis before attempting the same boot again.

## Retry the existing system

For the verified rescue condition above, use the rescue environment's supplied
`/sbin/techo5-retry` command once. It resets the failed-boot counter and restarts
the existing system. It does not install an image, reset configuration or
change the selected wake word. This is an administrative command on the
already installed TECHO5 system.

Keep power connected throughout startup. The reviewed boot script starts its
health check after platform initialization, waits 60 seconds, then checks that
the same daemon process survives another 30 seconds. A ring response or a
successful ping alone is not that checkpoint. Allow at least three minutes
for verification; if it is still unhealthy, inspect it rather than repeatedly
cycling power.

Do not disable the failed-boot guard or put the retry command into a loop. If
rescue returns, preserve the new logs and investigate the interrupted boot.

## Verify recovery

- Confirm the intended firmware and running slot, a stable daemon PID and a
  `0 healthy` boot counter.
- Compare configuration, pairing-key and personal-model hashes with the
  pre-retry receipt. Keep key material private.
- Confirm that Home Assistant's native satellite and speaker reconnect, and
  that Music Assistant's Sendspin client rejoins.
- Verify the configured SSH state. Rescue may provide key-only SSH even when
  the normal service's SSH setting is off; the recovered normal system should
  again honor that saved setting.
- Check fresh Bluetooth observations separately from a merely registered
  scanner. Test spoken responses and audible music only as a separate user
  acceptance step.

The failed-boot guard and supplied retry command are documented in the pinned
[init script](https://github.com/HuskerMinion/techo5-dot/blob/e369da6fb320c79d027acf25acfab7c4ab8c4cd9/tools/linux/init).
The successful-boot checkpoint is implemented in the pinned
[boot script](https://github.com/HuskerMinion/techo5-dot/blob/e369da6fb320c79d027acf25acfab7c4ab8c4cd9/tools/linux/rootfs/etc/techo5/boot.sh).

Related: [firmware updates](updates.md) · [Home Assistant](home-assistant.md).
