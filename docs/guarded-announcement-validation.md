# Guarded announcement validation — 2026-10-29

The experimental daemon is `v1.0.40-myshka.1.alpha.1`. It is built from shared
TECHO5 commit `892cdef6663acbb6ee963ed5862e363d61aff253`, with the versioned
[source overlay](../integrations/guarded-announcement/guarded-announcement.patch).
The installed stock binary's build metadata confirmed that upstream revision.

The [alpha release](https://github.com/ha-homelab/ha-techo5-dot/releases/tag/guarded-announcement-v0.1.0-alpha.1)
contains the daemon, build record, overlay, upstream daemon source, dependency
notices and the unmodified MPL-2.0 SIP dependency source. It contains no factory
firmware, household credentials, personal wake model or owner recording.

## Verified software behavior

- Twelve core admission/journal tests passed with the Go race detector.
- Four fake-player tests and one failed-journal voice-entrypoint test passed on
  Linux with the Dot build tag. They did not acquire a physical audio device.
- Twelve repository tests and seven maintenance tests passed.
- ARMv7 compilation, public-data checks and documentation checks passed.
- The required GitHub CI gate passed for source commit
  `f832dfafdec1199cc12f93b8dd1328229b3a75f9`, including the native tests,
  cross-compilation, CodeQL, dependency review and existing wake-classifier parity.
- The HA adapter passed 179 repository tests and 20 isolated tests using installed
  HA imports with fake I/O. The [adapter review](https://github.com/ha-homelab/ha-echomuse/pull/24)
  is maintained separately.

The tests cover duplicate and conflicting IDs, interrupted-process receipts,
storage failures, deadlines, exact-owner cancellation, preemption, busy refusal,
output availability and queue ownership. Normal activity does not wait behind
an entire announcement; it asks that announcement to stop, with bounded cleanup.

## Installed-system verification

Both physical Dots completed the explicit-hash maintenance procedure and its
normal watchdog acknowledgement. The running process and active on-disk daemon
matched the binary hash below on each device. The configuration and existing
SIP accounts were retained, with one extension per physical speaker.

After the shared Home Assistant restart, all four `echomuse_home` announcement
services were registered. Each device returned `cisco-announcement-v1`, a boot
identifier and all five required capabilities through the HA adapter. Three
additional sequential capability probes per device all succeeded. Voice and
media were idle, sounding indicators were off, and telephone status was ready.
This establishes control-path operation at verification time, not continuous
availability or audible performance.

The second installation overlapped HA startup. Its acknowledgement waited for
the native entities and completed within the existing deadline. Neither an
additional HA restart nor an override of the idle/capability checks was needed.

## Reproducible artifacts

- Native binary SHA256:
  `092d4469d5796c0413c1ef432021986fb30720f8ef0f62c9dd4961e0d46db21f`
- Source overlay SHA256:
  `805dcf3ee7443ccddfb7100b52de25b335bf08ec1c2f6e5831bcd828941a4fdd`
- Release archive SHA256:
  `96b7d128af5cdf049b0627e8bb63c92155da5506cc9ebd20abb2f18b049e2277`

Use the [build helper](../integrations/guarded-announcement/build.py) to reconstruct
the patched source and compile. The build record captures the toolchain and
flags; the archive hash describes this published package, not every future
archive of the same files.

## Acceptance limits

No test message, music, ringing or telephone call was initiated during this
maintenance session. Acoustic acceptance remains pending: audibility, pronunciation,
perceived timing and room-level behavior cannot be inferred from software tests.
There is no measured end-to-end latency claim.

`completed` means that local software output drained without a detected output
generation change, dropped frames or underruns. It does not establish that a
listener heard the announcement. An interrupted or unconfirmed request must not
be automatically replayed under a new ID.

The first release supports `busy_policy: skip` only. It does not promise music
pause/resume. Bluetooth-routed output is conservatively refused by its local
output check. The ordinary Assist announcement path remains unsuitable as a
fallback because it has no correlated job ownership.

This is a manual replacement of the active slot's daemon, not a new signed OTA
channel. A later upstream update can replace it; capability checks must fail
closed when the extension is missing. Automatic firmware installation should be
checked before a rollout. See the [maintenance procedure](../integrations/guarded-announcement/MAINTENANCE.md).

At this checkpoint Home Assistant offers upstream `v1.0.41` for both devices.
Automatic installation is off. Installing that stock update would replace the
custom daemon; port and revalidate the overlay before treating a newer upstream
version as a guarded-announcement upgrade. The upstream channel and signing key
were not changed by this deployment.
