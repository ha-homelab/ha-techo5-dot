# Additional Home Assistant controls for a TECHO5 Dot

The [capability package](../examples/home-assistant/techo5-capabilities-package.yaml)
and [standard Lovelace card](../examples/home-assistant/capabilities-card.yaml)
turn the v1.0.40 native entities and actions into bounded, device-specific
controls. They do not flash firmware, change the working wake word, adjust the
microphone frontend, or install a second service on the Dot.

Both files use JSON-compatible YAML. This is valid input for Home Assistant's
YAML loader and lets the repository verify the actual deployment files with
Python's standard library. No custom Lovelace card is required.

## Before installing

Check the native entity names on the device's HA page. Replace the following
placeholders throughout a private copy of **both** files:

- `echo_dot_example`: the native entity and ESPHome action prefix.
- `techo5_example`: a unique namespace for the added helpers and scripts.
- `TECHO5 example`: the matching human-readable name. Its slug must match the
  namespace, so `TECHO5 kitchen` corresponds to `techo5_kitchen`.
- `Echo Dot Example`: the exact device name in the `device` field of
  `esphome.techo5_gesture`. This can differ from its display name in HA.
- `light.example_kitchen_strip` and `light.example_kitchen_table`: two verified
  **light** entities. Do not replace them with generic sockets, heaters or a
  group containing unrelated loads. Leave clap control off if the mapping is
  not known. A missing or unavailable target prevents the light action.
- `sensor.example_battery_soc`: a numeric percentage in the range 0–100.
- `sensor.example_grid_power`: numeric watts, positive for import and negative
  for export. Convert a differently signed or scaled sensor before using it.
- The literal `201` in the `call_peer` script: the other Dot's verified private
  PBX extension. This is an example, not a number discovered on your network.
  Keep the fixed peer call unused until both endpoints are provisioned.

Do not reuse one helper namespace for two Dots. Timer IDs, ring snapshots and
opt-in settings belong to one source device. Use a private copy per Dot; live
addresses, entity mappings and credentials do not belong in the public repo.

The package expects the native Assist satellite, speaker and now-playing state,
ring, firmware update, mute, sounding, alarm, timer and phone-call entities.
`ready` becomes true after two seconds only when all of these agree that no
priority activity is taking place. Unknown or unavailable values prevent
effects, profile changes, announcements and light actions. Local timer/alarm
administration only requires a connected Dot.

For spoken notifications, alarm labels and reminders, open the device's
ESPHome integration options in HA and enable **Allow the device to perform
Home Assistant actions**. The native device uses that permission to request
TTS. Preserve the existing Bluetooth scanning and log-subscription options.
This grants the trusted device permission to invoke HA actions; ordinary
HA-to-device controls do not need it. A loaded package alone does not grant it.

## Install and enable

1. Merge the private per-device package through the installation's existing
   `homeassistant.packages` arrangement. Preserve the current configuration;
   do not replace `configuration.yaml` or an entire dashboard.
2. Run Home Assistant's configuration check. If these helper integrations are
   already loaded, reload the affected `input_boolean`, `input_number`,
   `input_text`, `input_datetime`, `input_select`, template, script and automation
   YAML configurations. If an integration is not loaded yet, arrange its normal
   initial setup separately. The package does not require a firmware restart.
3. Verify that the generated `binary_sensor.<namespace>_connected` and
   `..._ready` entities exist under the expected names. Resolve any old entity
   registry name collision before enabling controls.
4. Add the private card to the existing audio-player view. It supplements the
   media player; it does not replace it.
5. Turn on **additional controls**. All boolean opt-ins start off on first
   installation and thereafter restore their saved HA state. Merely loading
   the package does not enable a receiver, play a sound, create an alarm, toggle
   a room light or schedule an energy indication.
6. Enable individual options after their relevant checks below. Native AirPlay,
   DLNA and ambient-noise switches remain explicit card controls. The optional
   mappings do not change the buttons' built-in behavior.

Configuration checks and contract tests are not acoustic acceptance tests.
Verify the actual speaker and room once the user is available.

## What the controls do

### Ring scenes and energy

**Energy** uses red below 25% battery, amber from 25% to below 60%, and green
from 60%. In grid mode it uses amber above 50 W import, blue below −50 W export,
and neutral gray within ±50 W. Invalid readings prevent an energy scene.
These are configurable display bands, not battery protection thresholds.

The other manual scenes are a dim amber **Night light**, blue **Information**,
and green **Complete**. Duration is clamped to 1–30 seconds. In a dark room,
valid lux below 20 reduces the normal scene brightness. The optional periodic
energy pulse runs for five seconds every five minutes, only while idle.

Before changing the ring, the script snapshots its existing state. A voice
turn, music, microphone mute, call, alarm, timer or update takes priority. If one
starts during the indication, the script waits up to two minutes for idle and
restores the snapshot only if the ring has received **no intervening state
update**. It never rolls back a later manual change just because the apparent
color looks similar. Concurrent ring-scene requests are ignored.

The Dot reports RGB values scaled by brightness. The ownership check compares
color proportions and brightness separately, so dim colors still restore
correctly; a stale report, different hue or later state update does not qualify.

This is deliberately conservative: a changed ring, a long priority activity,
an interrupted script or an HA restart can prevent restoration. Dynamic
snapshots do not survive HA restart. **Clear manual ring** is an explicit
idle-only recovery control; it does not stop a sounding alarm or call. Native
indicator priority remains the responsibility of the installed firmware.

### Playback profiles

**Wi-Fi + BLE** turns off Bluetooth-phone reception and pairing, confirms both
are off, then enables the passive BLE proxy and Sendspin. **Bluetooth speaker**
turns off pairing and the BLE proxy, confirms both are off, then enables
Bluetooth-phone reception. A failed confirmation stops after ten seconds
without enabling the conflicting mode. Neither profile starts playback or
opens pairing automatically. AirPlay and DLNA settings are left as selected.

The profile sensor reports actual switch states, including **Radio contention**
if something outside this package enables both modes. The package does not
continually fight another client's settings. Select the appropriate profile
explicitly to resolve contention; native pairing remains a separate user action.

### Timers, alarms and announcements

**Start local timer** creates a 1–180 minute timer on this Dot. Its returned
`local:` ID is saved privately in a helper. Pause, resume, add five minutes and
cancel first list the device's timers, check that ID and the panel's label
namespace, then affect that one timer. Starting another timer leaves existing
ones running and changes which timer the panel controls. Assist timers and
timers created elsewhere are untouched. **Stop ringing alarm or timer** is the
native explicit control for whatever is currently ringing on this Dot.

Alarm helpers select a time, once/daily/weekdays/weekends, a label or reminder
text, and normal sound, light-only, or **Spoken reminder** mode. Editing them
does nothing until **Arm alarm or reminder** is pressed. The native clock and
time zone apply. The package records and
subsequently checks the matching alarm ID before enable, disable or delete.
Light-only alarms can brighten the ring before their scheduled time and hold
it afterward, according to native wake-light settings. Device-owned alarms and
timers continue while HA is unavailable; speaking an alarm label still requires
working HA/TTS and the device's permission to call HA actions.

**Spoken reminder** creates a native reminder at the selected time and repeat
schedule. It speaks the entered text without adding a technical label prefix.
The action explicitly sends an empty `ring_on`, so only the selected Dot is
included. The reminder's returned ID and original words are stored in separate
helpers. Its own enable, disable and delete buttons first check the exact ID,
the native `reminder: true` flag, and the unchanged original words. They never
cancel every reminder or modify the panel's alarm. If someone edits the
reminder text elsewhere, these controls refuse to act until a new reminder is
created through the panel.

Native reminders chime even during quiet hours. Their schedule remains local,
but speaking the words requires working HA/TTS and permission for the device
to perform HA actions. This differs from a normal announcement, which respects
native quiet hours. A reminder on a Dot has no persistent screen card to clear.

**Speak announcement** sends only the entered text to this Dot's native
`notify` action. The field and script cap text at 60 Unicode code points, which
cannot exceed the native 240-byte UTF-8 limit. Native quiet hours still apply.
This does not call `announce_house`, whose empty-text mode records a microphone.
No recording or microphone-streaming feature is enabled by this package.

### Calling the other Dot

The compact phone section shows registration and current call state, with
**Call other Dot**, **Answer** and **Hang up**. The call script accepts no number
argument: it can dial only the one extension selected in the private package.
It requires the Dot to be idle and its native phone state to be `Ready`; the
dashboard also asks for confirmation. No automation calls it. Answer and hangup
use the native button entities, so an active call can still be ended while the
additional-control helper is off.

This uses the existing private PBX and requires independently provisioned SIP
accounts. The package contains no account credentials and configures no account,
external dialing, automatic answering or drop-in. Direct TECHO5 house intercom
and nearest-device arbitration use a different house-word setup; they are not
prerequisites for the fixed PBX peer call.

### Noise-aware volume, without changing wake-word detection

The ambient-noise entity is a local numeric dBFS estimate, not calibrated dBA.
The suggested volume is 30% below −50 dBFS, 45% below −35 dBFS, or 60% in a
louder room, bounded by the user's cap. Unknown, invalid, or older-than-ten-minute
readings make the suggestion unavailable. A quiet room can produce no new
published value for a while; an unavailable suggestion is preferable to treating
an old reading as a current measurement.

The volume changes only on **Apply suggested volume**, while idle. It is a
normal persistent volume choice: the package does not restore an old volume
over a later human choice and does not chase music with repeated automatic
gain changes. It never modifies microphone gain, mixing, wake thresholds or the
personal wake-word model.

### Opt-in gestures and availability

Enable the native clap detector first and observe the originating event before
enabling **clap light control**. Only `double_clap` from the exact configured
device is accepted. If either assigned light is on, the action turns both off;
otherwise it turns both on. Both must be available. A three-second debounce
rejects a burst of repeated events. Dishes, children and television still need
an in-room false-trigger check.

**Action hold energy** adds a short energy indication to a hold event while
idle. It does not replace the Action button's native behavior. It ignores a
reconnect/initial event and checks idle again after a one-second delay, so a
native voice turn can win. Leave it off if the firmware's native hold behavior
in your room conflicts with the added indication. No custom mute or volume
button mapping is installed.

**Availability notices** creates one local HA notification after five minutes
of continuous unavailability and clears it after thirty seconds of recovery.
There is no reboot loop, credential rotation, message to an external service or
automatic power cycling. An extended offline Dot should be investigated for
power, cable and Wi-Fi issues rather than repeatedly restarted.

Two six-hour history cards show lux and ambient noise, then Wi-Fi signal and
available memory. They use the existing entities and normal HA Recorder
history; missing past samples are not backfilled. Internal memory and signal
units are preserved. A compact diagnostics section shows the last boot, free
storage, installed/available firmware, phone state and Sendspin state. No new
recording, polling service or database is installed.

## Validation and removal

Run `python3 -m unittest discover -s tests -q` and the repository's public/docs
checks. The package tests check every native action against the published live
v1.0.40 schema, required arguments, ownership guards, device-bound gestures,
fixed light targets, bounded waits, receiver switch ordering and dashboard
references. They cannot establish runtime compatibility with a different
firmware's schema; check again after an update.

For deployment, validate rendered templates and the full HA configuration,
then confirm the generated entities without invoking sound, alarms or room
loads. With a person present, test one short manual scene, one short timer,
the wake word and a spoken response. Check music and receivers separately.
Keep periodic energy and clap mappings off until accepted.

To remove the package, turn off its additional controls and optional mappings,
let any active scene finish, and remove its dashboard section and configuration.
Cancel or retain its device-owned timers, alarms and reminders deliberately:
deleting HA helpers does not delete schedules stored on the Dot. Receiver settings and
the last explicit volume choice also remain on the Dot.

The broader hardware, administration and privacy boundaries are documented in
[Capabilities](capabilities.md). Native action behavior is described by the
[upstream action guide](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/docs/actions.md).
