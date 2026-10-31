# Myshka signed firmware updates

This distribution targets **Echo Dot 2 / biscuit / RS03QR only**. It combines the
pinned TECHO5 Dot v1.0.44 system, the guarded-announcement/music-ducking patch,
and a downstream update client. It is not an installer for stock Alexa devices,
Echo Show, full-size Echo, Dot 3, or a different operating system.

## Why update the base?

The [original v1.0.44 release](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.44)
fixes AirPlay from a Mac using temporary IPv6 addresses. Merely replacing the
voice daemon misses the system firewall correction. Relative to v1.0.40, the
new base also includes AirPlay sender handoff, alarm enable/next-alarm controls,
media metadata actions and an opt-in **Record takes** facility.

The v1.0.42 custom-wake correction concerns **microWakeWord**. Our personal
«Привет, Мышка» runs with **openWakeWord**: its interpreter and bundled feature
models did not change across these source pins. Updating firmware does not
retrain it, replace the personal model, or justify changing its threshold.
Record takes stays disabled unless the owner explicitly enables recording.

## Trust and release channels

The downstream daemon trusts one fixed Ed25519 public key:

```text
VE1OZ3bqYzfSexvgIBbi6lGMkZW1VV22jnTTbogJBNw=
```

It fetches signed metadata from this repository's **myshka-beta** or
**myshka-stable** release. Metadata points to immutable version-tagged assets in
the same repository. The first published channel is beta; an unpublished stable
channel returns a check error, not an upstream fallback.

The client checks the signature, distribution, channel, Dot 2 target, version,
expiry, HTTPS asset location, SHA-256 and exact byte count. It fetches and checks
fresh metadata at installation, then validates the signed evidence again before
writing a slot. A failed fetch never authorizes installation from a stale cached
manifest. Stock TECHO5 signatures are not accepted by this distribution.

Versions use a normal numeric prerelease followed by a build suffix, for example
`v1.0.44-beta.202_myshka2`. The installed HA ESPHome integration strips the
underscore suffix before comparison. Always increase `beta.N` for a new beta;
changing only the suffix does not create a newer update. The older
`-myshka.2.beta.N` scheme failed actual HA version-ordering tests and is not used.

Channel metadata is valid for **180 days**. The client permits at most 366 days.
Before expiry, maintainers publish and promote a new signed release with a
higher beta number, even when the upstream source has not changed. The current
publisher keeps immutable release metadata unchanged; it is not a metadata-only
renewal command. Expiry blocks updates, not normal voice/media operation.
The signing seed is private; CI does not receive it and cannot sign releases.

## First migration and later updates

1. Confirm the existing Dot 2 system, pinned SSH identity, free space, A/B slot
   status and recovery access. Keep a compact private record of configuration
   hashes and critical files; never put device data into a release archive.
2. Build the bridge daemon **v1.0.44-beta.201_myshka2** from the pinned source and
   both patches. Use the guarded maintenance helper's idle checks, exact hashes
   and watchdog acknowledgement. This one-time daemon replacement establishes
   the downstream trust key; it does not update the entire system.
3. Publish and independently verify the signed **v1.0.44-beta.202_myshka2** full
   rootfs release, then promote its metadata to **myshka-beta**.
4. In Home Assistant, select **beta** under the device's Update channel. Re-enable
   its existing Firmware entity if it was disabled while it still checked stock
   releases. Confirm that the offered version and release link belong to Myshka.
5. Leave **Install updates automatically** off. Press **Install** on the Firmware
   entity, or call `update.install` with that single device's entity ID. Update
   one device at a time. Do not interrupt power during the slot write.
6. Verify reconnection, installed version, active slot, running/on-disk daemon
   hashes, wake model, name, pairing, SIP, Bluetooth and media availability.
   Only then move to the next device. Restore temporary administrative access.

Later releases need only steps 4–6. The existing ESPHome integration owns the
Firmware entity; no extra HACS updater or custom integration is necessary.
Home Assistant and Music Assistant entity IDs remain unchanged.

## What changes and what survives?

The rootfs archive contains the upstream system with the downstream daemon,
release identity, attribution and provenance. It does not contain a kernel,
OEM/device partition image, credentials or a trained personal model.

The native installer writes the **inactive A/B directory** and selects a trial
boot. Persistent `/data` retains pairing keys, names, SSH material, phone
configuration, preferences and personal wake-word files. Files manually changed
inside `/usr` or `/etc` are replaced; keep supported customization in persistent
storage. A rootfs rollback does **not** undo shared configuration changes.

## Rollback has limits

The existing boot supervisor commits a trial after the daemon's PID remains
stable. It does not prove that HA, speech, Wi-Fi, SIP or a wake model works.
Two failed trial boots trigger fallback to another good slot, but a running,
functionally broken daemon can still be marked good. Keep a verified recovery
route and explicitly test service health after installation. Inspect
`slotctl status` before selecting an existing good slot; never guess which slot
is old. No guarantee of automatic recovery is made for power or storage failure.

## Maintainer workflow

Use the [build, package and source instructions](../integrations/signed-ota/README.md).
The release directory is an allowlist: daemon, rootfs, corresponding sources,
provenance, manifest, signature and checksums. The publisher rejects any extra
file, preventing an accidental private file from travelling with release assets.

```sh
OPENSSL=openssl python3 integrations/signed-ota/publish.py private/release
OPENSSL=openssl python3 integrations/signed-ota/publish.py private/release \
  --publish --target FULL_PUSHED_SOURCE_COMMIT --notes-file private/release-notes.md
OPENSSL=openssl python3 integrations/signed-ota/publish.py private/release \
  --promote --target FULL_PUSHED_SOURCE_COMMIT
```

`--publish` never replaces existing version assets. `--promote` first downloads
every version asset and compares it with the verified local release, then updates
only the channel manifest/signature. GitHub cannot atomically replace this pair:
a check during promotion may fail its signature check and safely retry later.
Do not delete older version assets used by signed metadata.

Build and security checks retain the shared CI workflows. The extra OTA job
cross-compiles the current pinned base and tests signature/installation guards
alongside the retained announcement behavior. Installation receipts remain
private; public status records contain no network addresses or pairing secrets.
