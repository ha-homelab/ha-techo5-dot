# Guarded one-way announcements (experimental)

This source overlay targets the shared TECHO5 daemon at
[`892cdef6663acbb6ee963ed5862e363d61aff253`](https://github.com/HuskerMinion/techo5/tree/892cdef6663acbb6ee963ed5862e363d61aff253),
the `dot-v1.0.40` tag. The platform release is a separate repository and commit:
[`e369da6fb320c79d027acf25acfab7c4ab8c4cd9`](https://github.com/HuskerMinion/techo5-dot/tree/e369da6fb320c79d027acf25acfab7c4ab8c4cd9).
The earlier audit snapshot `2ae3c75776eb04f614295ceba7de3cfcf60e531f` is not the
release build pin.

The intended flow is a single locally synthesized audio file, followed by a
bounded, request-owned device announcement. It does not place a SIP call, answer
an incoming call, invoke ASR, or start an Assist conversation. Each physical Echo
keeps one existing SIP extension for ordinary telephone calls.

## Public HA contract

The optional `echomuse_home` update, version `0.4.0b2`, provides response-only
services. Its [source and review](https://github.com/ha-homelab/ha-echomuse/pull/24)
are maintained separately from this daemon overlay:

- `announcement_capabilities`: `entity_id`.
- `announcement_submit`: `entity_id`, `request_id`, `media_id`, `expires_at`
  (Unix UTC seconds), `preannounce: false`, `busy_policy: skip` (default) or `duck_music`.
- `announcement_status`: `entity_id`, `request_id`.
- `announcement_stop`: `entity_id`, `request_id`.

Submit, status and stop return the same `request_id` and a `status` from
`accepted`, `playing`, `completed`, `skipped`, `failed`, `stopped`, or `unknown`.
They may also return a bounded `reason`. Service submission is not playback
completion. `unknown` is not a reason to replay the same message automatically.

Capabilities use `protocol: cisco-announcement-v1` and boolean
`atomic_idle_guard`, `dedup`, `owned_cancel`, `honest_completion`, and
`deadline_enforced`. A client must require every flag, and must not fall back to
stock `assist_satellite.announce` or `media_player.play_media` when support is
absent. Stock announce has no request identity, may cancel a conversation, and
the reviewed TECHO5 implementation can also send the audio into an active call.
This overlay also removes that implicit SIP injection from ordinary Assist
announcements. Ordinary Assist announcements still lack the guarded request
contract and must not be used as a fallback.

The default `skip` mode preserves the first release's behavior: any music makes
it skip the announcement. The optional `duck_music` mode speaks over supported
local background music and temporarily reduces that music by the device's
configured `Media.DuckDB`. It requires both `duck_music: true` in the native
capabilities and the new native submit action. An older device is refused; the
adapter never silently converts a duck request into skip or an unguarded call.

Duck mode still refuses calls, active Assist turns, alarms, timers and another
foreground announcement, and respects Do Not Disturb and quiet hours. It owns
a temporary mixer claim rather than overwriting the user's master volume.
Finishing, cancellation, expiry or failure releases only that claim. This
allows volume changes made by the listener during speech to remain effective.
The guard belongs on the device, where calls, voice turns and audio playback
compete, not only in HA's potentially delayed state cache. A cancellation must
target the same request and must never issue a generic media stop or hang-up.
New ordinary activity preempts the exact announcement and waits at most two
seconds for its cleanup. It is not queued behind the full message. If cleanup
cannot complete safely, the new activity is refused rather than mixed into the
announcement. Alarms, audio-output changes and quiet-hours transitions also
invalidate the message. `completed` means an uninterrupted local software
playback drain; it does not prove that a person heard the audio.

Native actions use the existing encrypted ESPHome connection and direct JSON
responses: `guarded_announcement_submit`, `guarded_announcement_status`,
`guarded_announcement_stop`, and `guarded_announcement_capabilities`. Duck mode
uses the separate `guarded_announcement_submit_duck` action. Every action
takes a `request_id`; submit additionally takes `media_id` and `expires_at` as
strings. Request IDs have the form `announce-<32 lowercase hex digits>-<3 digits>`.
There is no dependency on event-bus acknowledgements. Receipts include the
protocol and current process `boot_id`.

The device records a request before allowing sound. Its bounded private journal
retains up to 512 receipts for at least 24 hours after expiry. A restarted process
returns `unknown` for an interrupted job and never automatically replays it.
Conflicting reuse of an ID, including a changed busy policy, is refused. Legacy
`skip` fingerprints remain compatible across the update. The deadline is at most 180 seconds ahead,
and decoded audio must be nonempty, at most 120 seconds, and fit the remaining
deadline. Missing/corrupt storage disables guarded dispatch.

Baya is selected during synthesis by the sender. Passing an existing file keeps
that voice independent of the receiver's conversation pipeline. The native path
requires a resolved HTTP(S) audio URL; HA resolves media-source identifiers before
submission. No spoken text is passed through the 240-byte native notification
field.

## Prepare and compile

Use a new ignored directory for every build:

```sh
python3 integrations/guarded-announcement/build.py \
  --work-dir private/guarded-announcement-build
```

`--source-cache /path/to/upstream-checkout` reuses a checkout containing the exact
commit; `--prepare-only` applies the patch without compiling. The helper refuses
to overwrite an existing build directory. Go module dependencies are pinned by
the upstream module files. The output includes a SHA-256/build record and an
explicit downstream version. This is a daemon development build, not a signed
stock OTA image. The helper has no deployment command.

The separate [maintenance helper](MAINTENANCE.md) provides a controlled manual
replacement for an existing installation, with explicit binary hashes, idle
checks and rollback. It does not flash a boot image or replace OTA signing keys.
After a device rename, HA may retain the original entity IDs while native action
names use the new device name. Keep `--prefix VERIFIED_ENTITY_PREFIX` for the
idle checks and pass `--service-prefix VERIFIED_CURRENT_ACTION_PREFIX` for the
capability acknowledgement. Verify the current action in HA; without this option
the helper uses `--prefix` for both. The `echomuse_home.announcement_*` services
bind through the target entity's current ESPHome connection and need no action
prefix.

## Acceptance and release boundary

The [dated validation record](../../docs/guarded-announcement-validation.md)
lists the published artifact hashes, software checks and acceptance limits.

Offline concurrency, deadline, deduplication and ownership tests must pass before
enabling the capability flags. Firmware compilation does not prove audio quality
or an audible end-to-end result. Acoustic acceptance is pending until an operator
explicitly permits playback. Do not play test audio, ring a device, or place a
test call during a quiet maintenance window.

Installing a replacement daemon restarts a shared service and interrupts its
connections. A quiet build or read-only health check does not authorize that
interruption. Check live idleness, retain a verified rollback binary, and arrange
a maintenance window before installing. Preserve the device's paired keys,
personal wake model, existing SIP account and upstream update trust key.

The source overlay is distributed with the [upstream MIT license](TECHO5-MIT.txt).
Other upstream components keep their own terms; see the preserved
[upstream NOTICE](TECHO5-NOTICE.txt).
Publishing a complete binary or system image also requires the applicable
third-party notices and source availability obligations. No factory firmware,
personal audio, credentials or signing keys belong in a release.
