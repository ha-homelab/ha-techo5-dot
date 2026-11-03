# TECHO5 v1.0.49 update review

The Myshka beta target is **v1.0.49-beta.203_myshka2**. It incorporates the
released TECHO5 Dot v1.0.49 base while retaining our signed update channel and
guarded announcements. This is a source and release record, not evidence that
the beta has been installed or heard on either household speaker. The last
recorded installation on both Dots is
[v1.0.44-beta.202_myshka2](status.md#october-31-2026--signed-myshka-ota-verified-on-both-dots).

## Exact upstream sources

Reviewed on **November 2, 2026**:

- [TECHO5 Dot v1.0.49](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.49),
  platform commit
  [`0c009e4f8baa94437cef933fc803691ff645842e`](https://github.com/HuskerMinion/techo5-dot/tree/0c009e4f8baa94437cef933fc803691ff645842e).
- [Shared TECHO5 v1.6.22](https://github.com/HuskerMinion/techo5/releases/tag/v1.6.22),
  daemon commit
  [`52f39926578b6b561e5556fec43f25c231f0eb5a`](https://github.com/HuskerMinion/techo5/tree/52f39926578b6b561e5556fec43f25c231f0eb5a).

The shared daemon advanced by 52 commits from our previous pin. The Dot platform
advanced by one commit, adding boot-reason tracking to the boot and shutdown
scripts. The shared repository already had unreleased changes beyond v1.6.22
when reviewed; those are not part of this target. Release tags, verified assets
and the [build lock](../integrations/signed-ota/upstream-lock.json) define the
inputs, not a moving `main` branch.

## Changes that matter on Dot 2

| Change | Why it matters | Existing-setting behavior |
| --- | --- | --- |
| Separate wake threshold during playback | Allows calibration while music or a reply is playing without changing the quiet-room threshold. | An unset value retains the previous formula: quiet threshold minus 0.10, with a floor of 0.50. The personal model at 0.50 therefore keeps its prior effective cutoff. |
| Wake-word retry over an alarm or timer | A near detection briefly quiets the ring so a second attempt can be heard. | No wake model replacement is needed. Actual recognition remains an acoustic test. |
| HA connection cleanup | A closed API connection releases the voice session, and a new subscription can take over. | Encrypted pairing and the selected Assist pipelines remain separate settings. |
| End-of-speech pause | A configurable 0.6–2.0 second pause can accommodate hesitation within a sentence. | Default remains 0.6 seconds. A longer value also delays the end of every utterance. |
| Wake and cancellation evidence | `esphome.techo5_voice` includes the peak `wake_score` and distinguishes stopped, interrupted, cut-off and answered-elsewhere turns. | Existing `ended` classifications remain available. Events may briefly wait for the final wake score. |
| Speech-text privacy switch | `Send voice text` controls transcript/reply copies in device text entities, voice events and diagnostic logging. | Enabled by default, as before. Turning it off does not remove old Recorder history or prevent the chosen speech/conversation provider from processing a request. |
| Runtime diagnostics | Adds CPU usage, wake-loop load, frame rate, worst frame and last boot reason. | These support diagnosis; a high load average alone is not equivalent to high CPU use. |
| DHCP renewal after network change | A speaker that moves to another saved network requests an address there. | Saved Wi-Fi credentials need not be replaced. This is relevant to moving a Dot between rooms or access networks. |
| Intercom background-noise adaptation | The far end counts as speaking only above its own noise floor, allowing a local hang-up word in a quiet call. | SIP account configuration stays separate; call and hang-up behavior still require a real call test. |
| Music Assistant queue cleanup | A cleared queue no longer leaves the old remote track held as paused. | A deliberately paused queue still retains its track. Guarded announcement mixing must continue to pass its own tests. |
| Clap filtering and Spotify diagnostics | Adds a Strict clap mode and logs rate-limited librespot warnings/errors. | Normal clap sensitivity stays the default; logging does not fix Spotify account or track-key failures. |

These changes span the official
[v1.0.45](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.45),
[v1.0.46](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.46),
[v1.0.47](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.47),
[v1.0.48](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.48) and
[v1.0.49](https://github.com/HuskerMinion/techo5-dot/releases/tag/dot-v1.0.49)
releases. The table describes the implementation and documented defaults,
not measured improvements in this home.

## Optional features and scope

Wi-Fi quiet hours can deliberately disconnect the speaker on a schedule. They
remain off unless configured; enabling them also makes HA control unavailable
during the window. Device-local timers and alarms can still ring.

News-podcast playback is new in the **direct assistant**. It does not add news
skills to our existing HA `Local Russian Home` conversation agent. The beta does
not change that agent, its data policy, the Russian voice or the source of speech
recognition. Display effects, Show 8 boot-loader work and other screen-only
changes in the shared release do not add a screen to Dot 2.

The personal **«Привет, Мышка»** model remains a separately installed
openWakeWord asset. It is not retrained, replaced or included in public firmware
archives by this update. Pairing keys, House word, Wi-Fi/SIP settings and other
device data also remain outside the release artifacts.
The openWakeWord runtime, TFLite interpreter and bundled feature-model source
trees are unchanged between the two shared release pins.

## Downstream corrections

The new upstream `Store.UpdateChecked` path now applies our existing silence
policy interruption rule. An accepted change to Do Not Disturb or quiet hours
cancels the owned announcement; a rejected or unrelated change does not. A
failed persistence attempt restores settings while conservatively leaving the
announcement cancelled. Regression tests exercise these cases without devices.

The builder reads its daemon pin and permitted version prefix from the same
lock used by the packager. Packaging rejects a differently labelled base before
signing. The release compiler is pinned to Go 1.27.3 and its actual version is
checked from inside the Go module, so a local toolchain-selection failure cannot
silently produce a differently built release.

## Compatibility checks required for publication

The shared daemon now uses Go 1.27 and upstream `go-esphome-device` v0.0.18;
this release builds with Go 1.27.3, matching the upstream patch version.
Reapplying a patch cleanly is insufficient: compile the Dot target and run the
native announcement and update tests against these exact inputs. In particular,
verify the wire-correlated action replies used by the HA announcement adapter,
busy refusal, expiry, deduplication, cancellation ownership and mixing cleanup.

HA identity reporting changed: the model stays stable while the firmware is
reported as the TECHO5 project version alongside its ESPHome compatibility
version. Maintenance checks must not require the old version-bearing model
string or mistake the compatibility version for the installed firmware.

Our Ed25519 key, `myshka-beta`/`myshka-stable` feeds, immutable release assets and
monotonic beta number remain the update boundary. Retain manifest verification,
architecture checks and A/B rollback. Do not replace the downstream updater
with the original project's channel while rebasing. See the
[OTA guide](signed-ota.md) and
[guarded announcement contract](../integrations/guarded-announcement/README.md).

## Known limits and follow-up checks

- **False wakes are not proven fixed.** Upstream still has reports such as
  [#405](https://github.com/HuskerMinion/techo5/issues/405), and the room-floor
  minimum remains under investigation in
  [#377](https://github.com/HuskerMinion/techo5/issues/377). New diagnostics make
  measurement easier; they do not justify lowering our threshold or advertising
  a new recognition result without recordings and held-out checks.
- **Nearest-device selection needs a shared House word.** An enabled switch
  alone does not establish working arbitration; upstream
  [#412](https://github.com/HuskerMinion/techo5/issues/412) documents the missing
  readiness warning. Preserve the configured secret and check actual decisions
  across Dot and Show devices after a future installation.
- **HA wake confirmation is a different recognizer.** Its pipeline must refer
  to a wake-word ID offered by the HA engine; stale IDs can look like a normal
  rejection ([#411](https://github.com/HuskerMinion/techo5/issues/411)). A custom
  model installed only on the Dot is not automatically installed on that engine.
- **Use one HA subscriber for the Bluetooth proxy.** A second HA instance can
  take over advertisements without restoring the first subscriber automatically
  ([#402](https://github.com/HuskerMinion/techo5/issues/402)). Isolated transport
  tests must use fake devices, not pair a test HA to the production proxy.
- **Server-side latency is separate.** This firmware update does not make the
  local conversation model faster or repair a custom HA integration's API
  compatibility. Speech capture, recognition, reasoning, synthesis and playback
  require separate timing evidence.

Source/build validation, publication and installation are separate milestones.
Any later deployment should record the actual running version and hash, current
HA availability, wake/model settings, Bluetooth advertisements, one-shot
announcements, music mixing, reconnect behavior and attended Russian speech.
Keep unperformed acoustic acceptance explicitly open in the
[status record](status.md).
