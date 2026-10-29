# Announcements over music — beta 1

`v1.0.40-myshka.1.beta.1` adds an opt-in music-ducking mode to the
[guarded announcement contract](../integrations/guarded-announcement/README.md).
It is a downstream daemon built from TECHO5 revision
`892cdef6663acbb6ee963ed5862e363d61aff253`, not a signed upstream OTA image.
The matching Home Assistant adapter is `echomuse_home` **0.4.0b2**.
The previous [alpha validation record](guarded-announcement-validation.md)
remains a separate historical record.

## What changes

With `busy_policy: duck_music`, supported music continues while a temporary
mixer claim lowers it beneath the announcement. The device's existing **Music
ducking** setting controls attenuation; the pilot uses **−15 dB**. The master
volume is not saved and overwritten, so the listener's own volume adjustment
is retained. Completion, cancellation, error and expiry release only the
announcement's claim. Independent ducking requests remain effective.

The original `busy_policy: skip` is unchanged and remains the default.
Calls, active Assist, alarms, timers, another foreground sound, Do Not Disturb
and quiet hours still block a new announcement. New ordinary activity can
preempt the exact announcement. A change of music producer or output route
also stops it conservatively; the message is not automatically replayed.

The verified producer paths are the native media Stream and Sendspin local
output. A remote player's `playing` state alone does not establish usable local
audio. Unknown or external-only routes are refused. Bluetooth output is still
outside this guarded local-output contract.

## Using it from Home Assistant

1. Query `echomuse_home.announcement_capabilities` for the satellite. Require
   all five base flags plus `duck_music: true`.
2. Render the announcement once with the configured TTS voice. Keep its audio
   file available until the request expires.
3. Call `echomuse_home.announcement_submit` with a fresh request ID, the rendered
   media path, an integer deadline no more than 180 seconds away,
   `preannounce: false` and `busy_policy: duck_music`.
4. Query `announcement_status` using the same ID. Submission is asynchronous.
   To cancel, use `announcement_stop` with that ID; do not stop the music player.

The adapter dispatches the separate native `guarded_announcement_submit_duck`
action. Missing support is refused without falling back to ordinary playback.
Retries query the original job. Changing a request's policy under the same ID
is a conflict; old skip fingerprints remain valid after upgrading.

## Verification

Core admission and persistent-journal tests passed with the Go race detector.
Linux ARM64 tests with the Dot build tag covered fake speaker output,
foreground accounting, cancellation and preemption, independent duck ownership,
forced ducking when ordinary conversation is configured to pause music,
Sendspin source readiness and unavailable-journal control access. The Linux
tests did not play audio on the physical Dots.

Foreground completion counts actual speech frames written to the device.
Continuing background frames cannot impersonate completed speech, and speech
does not wait for the entire music stream to end. Software completion still
does not prove that a listener heard the message.

The HA source passed **190 repository tests and 23 isolated runtime tests**.
The repository's standard tests, seven maintenance tests, public-data audit,
documentation checks and ARMv7 compilation also passed. Shared CI repeats the
native tests and compilation for the versioned patch.

## Installed pilot — October 29, 2026

Both Dots completed the controlled daemon replacement and normal watchdog
acknowledgement. Each running process and on-disk daemon matched the beta hash
below, and the HA adapter returned all five base flags plus `duck_music: true`.
Existing pairing, wake models and SIP account files were not rewritten by the
installer. Temporary SSH on the second Dot was switched off again.

HA 0.4.0b2 is active after one coordinated restart. Its four changed files match
the published source; the pilot's existing household init, intent and policy
files remain byte-identical. The service schema exposes both `skip` and
`duck_music`.

The first uncompressed upload hit the 90-second transfer limit before any
active-file replacement. Its partial staging file was removed after confirming
the alpha daemon still matched its hash. The successful installs used compressed
SSH transfer with the same expanded-file SHA-256 checks. No guard or watchdog
was bypassed.

## Audiocenter acoustic acceptance

The operator-authorized check used the first Dot's existing Music Assistant
queue through Sendspin. Native and Music Assistant playback were both observed
before submission. The legacy policy returned `skipped / audio_busy`; the
explicit duck request progressed to `completed` while that same music queue
continued. A duplicate returned the original completion without another
announcement. Master volume remained **23/30** throughout. After the test, only
that unchanged test queue was stopped, leaving both players idle.

The listener confirmed hearing the announcement and the music attenuation in
response to the mixing/restoration check. This confirms this short Audiocenter
scenario. It does not establish prolonged-stream reliability, all output
protocols, or acoustic acceptance of mixing on the second Dot. The second Dot
has passed installation, running-hash and capability checks.

## Reproducible artifacts

- Daemon SHA256:
  `c615f3a9255a1f93bd9cf100eb0dc198569935131e4ce550536e3729ae11ca1b`
- Source patch SHA256:
  `26b15d4db822b7b379774ba120eea3bb8a0edc0386b500e3a52313d6d4a6947d`
- Native release archive SHA256:
  `f5c9b6bb4a34e807a7d3fe03bf8147a27f71ffdee0a7ea03e8b9b8e2ce937f07`
- HA 0.4.0b2 ZIP SHA256:
  `cb70a42d677c014d8fae76f491ab68c377ead67e5bd54f2c9f78f97fd8045896`

The native package preserves the upstream MIT/NOTICE and supplies the unchanged
MPL-2.0 diago dependency source. It includes no factory image, credentials,
personal wake model or recordings. The HA ZIP is the full repository component;
the household pilot uses a targeted four-file overlay to preserve its existing
intent/policy implementation. These are deliberately distinct installation scopes.

Use the [maintenance procedure](../integrations/guarded-announcement/MAINTENANCE.md)
with exact old/new hashes. Automatic upstream OTA installation remains disabled
for this pilot: stock firmware would replace the custom daemon. The upstream
signing key and update channel are unchanged.
