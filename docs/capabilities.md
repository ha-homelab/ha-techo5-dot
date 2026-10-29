# Making a TECHO5 Dot useful beyond voice

This is a capability audit of an Echo Dot 2 running **TECHO5 v1.0.40** on
October 29, 2026. A live Home Assistant inventory found **186 entities and 44
native actions**. USB inspection confirmed the installed release and tools.
The initial audit did not enable services, record audio, play media or place
calls. The subsequent implementation is documented in the
[deployment record](capability-deployment.md),
[HA controls guide](capability-package.md) and
[access and receiver guide](capability-access.md). The observed-state table
below is the original baseline, not a current deployment inventory.

The most useful architecture is a small audio/sensor endpoint with Home
Assistant automations and local server-side speech, history and reasoning.
Installing many independent services on the Dot adds maintenance without
improving its microphones or speaker.

All examples use the placeholder prefix `echo_dot_example`. Replace it with the
device's actual entity/action prefix after checking the HA device page.
The [complete action schema](reference/actions-v1.0.40.json) contains names and
field types, never live credentials or configuration values. Presence of a
generic action does not prove that screen-dependent behavior works on a Dot.

## A practical feature plan

| Capability | Observed state | Useful next step | Constraint |
| --- | --- | --- | --- |
| Personal wake word and local Assist | Configured | Preserve the working frontend | Changing microphone mixing needs new acoustic tests |
| Lux sensor | Working | Light-aware night routines and ring brightness | Its location and orientation affect readings |
| Health sensors | Available | Add a maintenance card and history | Internal temperatures are not room temperature |
| Ambient-noise sensor | Off | Publish a local numeric noise trend | dBFS, not calibrated dBA or proof of occupancy |
| Button events and RGB ring | Available | Appliance/energy feedback and manual controls | Native button/voice/alarm behavior still takes priority |
| Double-clap detector | Off | Observe events before assigning an action | Kitchen sounds can produce false events |
| Sendspin | Connected | Keep Music Assistant as the main music route | Playback quality still needs listening tests |
| AirPlay receiver | Off | Playback from a Mac or iPhone | AirPlay 2 preference being on is insufficient |
| DLNA renderer | Off | Direct playback from local media clients | No seek in reviewed implementation |
| Passive BLE proxy | On | Forward supported sensor advertisements | No active GATT connections on this Dot build |
| SIP/intercom | Actions available | Extend the local phone system | This audited unit's SIP account was not yet configured |
| SSH | Off; a public key already stored | Key-only recovery and inspection | Root access; preserve existing keys |
| Setup page / remote API | Off | Use for a specific administration need | Separate access mechanisms and restrictions |

This table describes the audited unit, not every Dot or every future release.

## Administration: what each access path gives you

### USB console

The installed system provides a serial console through its USB device/gadget
connection. It is the recovery path when HA, Wi-Fi or the normal service fails.
Identify the device by its USB serial; a changing device number or cached IP
address is insufficient. Keep this path available during system maintenance.

USB attachment to a NAS does not turn the Dot into a USB microphone, USB sound
card or general USB host. Those are different gadget/driver functions and would
require a separate hardware/kernel project.

### SSH and file transfer

Dropbear is installed. Its supported configuration is **root, public-key-only
SSH on port 22**, with password authentication disabled. There is no SSH
password to recover from Home Assistant.

1. Preserve the existing authorized public keys privately. The audited unit
   already had one key; do not assume its key list is empty.
2. Enroll the intended public key through the encrypted native action
   `esphome.echo_dot_example_ssh_keys`, field `keys`. This replaces the complete
   list, so include the existing keys that should retain access. Never send a
   private key to this action.
3. Enable the device's native SSH switch and verify an actual key-based login.
4. Use `ssh -i <private-key-file> root@<device-address>` for administration.
   The audit found no SFTP server; use `scp -O` or a bounded SSH stream for file
   transfer when needed.

Keys and normal settings live on persistent userdata. Disabling SSH stops new
connections but does not terminate already established sessions. Access from
outside the home should use the existing home-network VPN; the built-in
Tailscale/NetBird documentation covers other TECHO5 device families, not a
verified feature of this Dot image.

**Telnet adds no useful access path here.** No `telnetd` was found on PATH or
listener on port 23. There is no native Telnet toggle. Installing a plaintext
root login would duplicate the stronger supported SSH and USB paths.

### Web setup and remote API

The setup page is a separate HA switch, on the device's HTTP port 8181. Follow
its local authorization prompt; the reviewed implementation uses a device
button press to admit a browser session. It is not an SSH login. Close the setup
page when the maintenance session is complete.

The optional remote API uses `/api/v1/` on the same port. Its key is created on
the setup page and displayed once; losing it requires a new key. Requests use
HMAC signatures, a timestamp and a nonce. This authenticates requests but does
not encrypt their contents. Use it only for a defined LAN/VPN client.

- `GET /api/v1/device`: identity, release and uptime.
- `GET /api/v1/entities`: available settings/readings, ranges and writeability.
- `POST /api/v1/entities/<id>`: permitted everyday settings only.
- `GET /api/v1/logs`: bounded redacted log streaming.

It cannot enable SSH, recording, calls, privacy features or the API itself;
cannot install updates or restart the device; and cannot execute arbitrary
Home Assistant actions. Some room/device names can remain in redacted logs, so
they still belong in private diagnostics. Native HA is already an adequate
control API for most automations; a second API is optional.

Sources: [security implementation][security], [web authorization][web],
[remote API documentation][setup].

## Sensors, buttons and light ring

**Lux** is a real ambient-light sensor. USB inspection identified `tsl2584tsv`;
HA reported 83 lx at the audit location. Use it for room-aware ring brightness
or evening routines. Do not treat a measurement beside the NAS as the kitchen's
lighting measurement.

**Ambient noise** is enabled by
`switch.echo_dot_example_microphone_ambient_noise_sensor`. Its
`sensor.echo_dot_example_microphone_ambient_noise` publishes a five-second
numeric average computed locally, without recording or transmitting audio.
The scale is dBFS. Readings are held or unavailable in some playback, voice,
ringing and mute states. Filter unknown/unavailable values and combine with
context; do not use it alone for occupancy or a sound-level safety threshold.

**Diagnostics** already include Wi-Fi signal/traffic, available memory, free
space, last boot, load, CPU/radio temperatures, BLE advertisement rate and
Sendspin state. The metrics interval was 300 seconds; temporarily reducing it
can help a focused investigation. Linux load is not CPU utilization: vendor
driver tasks can contribute while waiting. Prefer trends and correlation with
boot/availability to an unconditional reboot automation.

The [read-only maintenance card](../examples/home-assistant/maintenance-card.yaml)
uses existing entities and has no tap or hold actions. Adding the card does not
enable the optional noise sensor or any network service.

**RGB ring:** `light.echo_dot_example_ring_led_ring` supports color, brightness
and built-in effects. Suggested HA routines include battery-charge bands,
grid import/export, a finished dishwasher and a gentle night light. Preserve
the prior state and defer to listening, speaking, mute, timers, alarms and
calls. The hardware has 12 RGB segments, but an arbitrary per-segment drawing
API was not established by this audit. Room-following effects are sound
visualizations, not motion sensing.

**Four physical buttons** already emit events:
`event.echo_dot_example_action_button`, `..._mute_button`,
`..._volume_down_button`, `..._volume_up_button`.
The observed event types are `press`, `hold`, `long_hold`; double press is not
one of them. Events supplement the buttons' existing functions. A new mapping
must account for muting, volume changes, Assist, call control and long-press
Bluetooth behavior. Prefer an explicit idle-only light or scene action to
blindly toggling arbitrary appliances.

**Double clap** is separate: enable
`switch.echo_dot_example_microphone_clap_gesture` to receive
`esphome.techo5_gesture` with `gesture: double_clap` and the device identity.
There is no light action until an automation is assigned. It does not operate
during music, its own audio, a voice turn or a call. Observe false events from
cutlery and dishes before using it as a kitchen control.

Sources: [sensor and gesture documentation][setup], [button implementation][buttons].

## Music, speech, alarms and communication

Keep Sendspin/Music Assistant as the main media route. Optional alternatives:

- **AirPlay:** enable the actual `airplay` receiver switch. An enabled
  `airplay_2` preference alone does not start it. Sender volume control is a
  third independent switch. Verify discovery and playback after enabling.
- **DLNA:** a local renderer for compatible NAS/media clients; reviewed support
  includes MP3/FLAC/WAV, without seeking. Enabling it lets LAN clients initiate
  playback.
- **Spotify Connect:** requires a suitable Spotify account; not a benefit for
  a household using only Plex/local media.
- **AUX/headphones:** the built-in 3.5 mm output can feed existing amplified
  speakers. This is usually more useful than maximizing gain on the small
  internal speaker. Extra speaker gain can clip and impair wake recognition.

The Bluetooth phone-audio receiver and a continuously scanning BLE proxy share
the radio. Upstream warns of stutter with both; choose a music-over-Wi-Fi
profile with BLE, or a deliberate Bluetooth-speaker profile with proxy scanning
off. Do not enable both as an automatic "maximum features" preset.

**Spoken notifications:** use the per-device native `notify` action. All seven
fields are required: `message`, `title`, `icon`, `chime`, `speak`, `tag`,
`seconds`. `speak: "on"` needs the device's permission to perform HA actions.
The documented message limit is 240 UTF-8 bytes, which matters for Russian;
quiet hours suppress sound. Longer energy reports belong in the normal HA
speech/announcement pipeline.

Do not confuse this with `announce_house`: reviewed docs say text announcements
only chime on a Dot, and **empty text starts microphone capture** for a house
announcement. An empty string is not a harmless announcement test.

**Local timers and alarms** continue without a working HA connection once set.
`timer_start` takes `duration` and `label`; preserve the returned timer identity
for pause/resume/cancel. Native timers and HA Assist timers are separate stores.
Alarm variants include silent and light-only routines. v1.0.40 uses
`alarm_turn_on_id` / `alarm_turn_off_id` for ID-based toggling. A recurring
reminder can ring locally; speaking its label still needs HA/TTS. A ring sunrise
can also drive an existing brighter lamp via the wake-light sensor.

**SIP and intercom** offer another use without new hardware. The audited unit
had native account, contact, dial, answer and hangup actions but no configured
SIP account. Provisioning remains separate from exposing those controls.
House intercom and nearest-device wake arbitration require matching private
house words; an enabled arbitration switch alone is not proof of coordination.
Drop-in can answer without someone pressing a button, so it is a separate
privacy choice, not required for normal intercom.

Sources: [music and communication documentation][setup], [native actions][actions].

## Hardware and extension boundaries

The running image is ARMv7 with about 481 MiB usable total RAM. At the audit,
roughly 423 MiB was available, with 1 GiB free on userdata and 549 MiB in the
slot store. These are point-in-time readings, not application reservations.

- The Dot BLE build forwards advertisements but has no active GATT central:
  its `openCentral` implementation is absent. This is not a hidden HA switch.
  It can help supported advertisement-based sensors; it cannot replace every
  Bluetooth adapter or operate arbitrary BLE locks through active connections.
- There is no camera, PIR/mmWave occupancy sensor, humidity/CO2 sensor, or
  Zigbee/Thread coordinator hardware. Internal chip temperatures are not room
  temperature; BLE RSSI and noise are only weak context for presence.
- Keep ASR, LLMs, expressive Russian TTS, story/riddle generation and energy
  history aggregation on local HA/NAS/Mac services. An 8B/14B model or a large
  speech stack is not a practical fit on this device.
- The working personal wake model uses the current microphone frontend.
  Beamforming, all-microphone averaging and other mixing options are candidates
  for controlled near/far A/B tests, not automatic upgrades to a working model.
- `echod` owns the audio paths and coordinates radio use. A second ALSA capture
  process or independent Bluetooth manager can break that coordination.
- Do not probe undocumented vendor GPIO/sysfs attributes indiscriminately.
  Some vendor-driver paths are unsuitable even though a file is visible.

The image has `apk`, but not Python, Node, Telnet or SFTP executables on the
audited PATH. Installing a package is technically different from supporting
it across upgrades. OTA clears and repopulates the inactive rootfs slot:
manual additions under `/usr` and `/etc` do not reliably survive. Userdata
persists, but merely copying a binary there does not provide a supported
startup/plugin contract.

For deeper development, use a reproducible maintained firmware/rootfs fork
and its own release testing, or preferably an external HA integration/server
using the existing native actions. Retain USB recovery and bounded private
receipts. Do not blanket-upgrade the base distribution or overwrite the vendor
kernel as part of installing a convenience tool.

For a responsive assistant, route common light, outlet, timer and energy-summary
requests through explicit local HA intents. Reserve the local language model
for open-ended questions and creative dialogue. Grant home-control tools an
explicit device/service scope and keep household history local. None of that
requires replacing the working satellite firmware or uploading household
context to an unrestricted public model.

Sources: [Dot BLE implementation][ble], [rootfs slot manager][slots],
[upstream build guide][building].

## Suggested order of implementation

1. Add the maintenance card and health history; enroll and test key-only SSH
   if ongoing remote administration is wanted.
2. Enable the numeric noise sensor and, if used, AirPlay. Observe behavior
   before writing automation around the new readings.
3. Add one ring/energy routine, one idle-safe button routine and a kitchen
   timer/notification flow, each with explicit source and target mapping.
4. Finish SIP provisioning and house-word arbitration checks. Keep drop-in,
   recordings and microphone streaming as separately chosen functions.
5. Evaluate microphone changes only with repeatable recordings and held-out
   near/far tests. Keep the working personal wake model available for rollback.

The inventory and examples are a proposal, not a record of those switches being
enabled. Live schema existence was verified independently of source behavior.
The reviewed shared-source commit below is newer than the release and is not a
proven binary source pin. Access-related files were also compared with the
pre-release source; matching files strengthen the evidence but do not attest
the entire firmware binary. Re-check the live schema after a future update.

[setup]: https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/docs/setup.md
[actions]: https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/docs/actions.md
[security]: https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/security/rootssh.go
[web]: https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/web/web.go
[buttons]: https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/buttons/buttons.go
[ble]: https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/bluetooth/central_dot.go
[slots]: https://github.com/HuskerMinion/techo5-dot/blob/e369da6fb320c79d027acf25acfab7c4ab8c4cd9/tools/linux/rootfs/usr/local/sbin/slotctl
[building]: https://github.com/HuskerMinion/techo5-dot/blob/e369da6fb320c79d027acf25acfab7c4ab8c4cd9/docs/building.md
