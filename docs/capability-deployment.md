# Additional capabilities: deployment and verification

This records the October 29, 2026 expansion of the first Echo Dot 2 on
TECHO5 v1.0.40. The second Dot was not reflashed or reconfigured by this work.
It remains the existing peer for home telephone calls. Public examples use
placeholders; live mappings and deployment receipts remain private.

## Device services

The existing authorized Mac key successfully logged in through native,
password-disabled SSH. Its host key was checked against independent USB
evidence before accepting the network connection. No key list, firmware,
root filesystem package or recovery partition was replaced.

AirPlay 2 was enabled and its receiver, timing process and TCP 7000 listener
were verified. DLNA returned valid device and transport descriptions with
HTTP 200. Sendspin remained enabled. These checks establish service readiness,
not playback quality from every sender.

The local ambient-noise sensor now reports numeric dBFS values. It does not
record or upload audio. The physical lux sensor remains available. Metrics
publish every 60 seconds instead of every 300 seconds. The native clap detector
is enabled; its optional mapping to two verified light entities remains off
until an in-room false-trigger check.

The first Dot registered with the existing private PBX. The PBX confirmed an
available contact; no call was placed. Its existing transport policy was
preserved. Home Assistant permission for device-originated actions was enabled
through the normal ESPHome options flow so that native spoken reminders and
notifications can request TTS. Passive Bluetooth scanning and log-subscription
settings were preserved.

## Home Assistant controls

The [package](../examples/home-assistant/techo5-capabilities-package.yaml)
provides 13 scripts and five automations. Its [card](../examples/home-assistant/capabilities-card.yaml)
uses standard Lovelace components, including six-hour sensor history.

- Temporary ring scenes: battery/grid indication, night light, information,
  complete, and explicit clear. Scenes yield to voice, calls, music, mute,
  updates, alarms and timers. Restoration requires unchanged ownership.
- Local timers and alarms, including a light-only alarm and a spoken reminder.
  Subsequent actions check the saved device-owned ID before changing anything.
- Explicit short announcements and an optional volume suggestion based on
  recent ambient noise. Wake thresholds and microphone gain are untouched.
- Mutually exclusive Bluetooth-speaker and Wi-Fi-plus-BLE profiles. Selecting
  a profile does not start playback or open Bluetooth pairing.
- An explicit fixed-peer telephone call, plus native answer and hangup.
- Optional double-clap lighting, Action-hold energy indication, periodic
  energy indication and a debounced local availability notification.

See the [setup and operating guide](capability-package.md) for defaults,
physical acceptance checks, ownership rules and limitations. An available
firmware update does not disable these controls; an update in progress does.

## Web access and house links

Native web setup requires an actual Action-button press to admit the waiting
browser. This is separate from authorized SSH access. The owner admitted the
browser and created a Remote API key. It was saved only in the ignored private
directory with mode 0600. The [read-only API client](../scripts/remote_status.py)
successfully made signed device and entity requests; the live inventory
contained 169 parameters. The setup and key steps are in the
[access guide](capability-access.md).

Native house features need the same private house word on both devices.
The owner saved the same phrase through both admitted setup pages; both pages
then confirmed a configured word. Nearest-answer settings remain enabled on
both Dots. In the subsequent real wake-word check, the owner heard one Dot
respond. The available first-Dot log shows its local answering decision; it
does not prove that both microphones heard that particular utterance. A
verified peer-yield log would provide stronger arbitration evidence.

House settings sharing and Drop-in remain off. Direct house intercom is
configured but two-way audio has not been tested. The existing PBX route is
independent of the house credential. In this build, the House word form is
under **Sound & Voice → Announcements**, despite older UI text referring to
Connections.

Drop-in, continuous microphone streaming and stored wake clips remain off.
They are not prerequisites for the controls above. Telnet adds no useful
capability to the authenticated SSH channel. Active BLE GATT, absent hardware
sensors and a large local language model cannot be created by enabling
additional switches on this Dot.

## Verification boundaries

Full Home Assistant configuration validation, runtime template rendering,
entity readback and limited reversible control checks are separate from
acoustic acceptance. Receiver discovery is not proof of uninterrupted music;
PBX registration is not proof of intelligible two-way audio. Test those with a
person present before enabling recurring or sound-triggered household actions.

The installed package passed HA configuration checks and all 105 template
renders. Live checks verified timer pause/resume/extension/cancellation,
alarm and reminder creation/disable/deletion, and ring restoration. No test
alarm or timer remained. A firmware-specific RGB reporting difference was
found during that test: feedback includes the selected brightness. Comparing
color proportions separately from brightness fixed scene ownership and is
covered by regression tests.

The card was added beside the existing Dot controls in the audio-player view.
Additional controls and availability notices were enabled. Clap lighting,
Action-hold scenes and periodic energy scenes remain explicit opt-ins. The
normal wake model, threshold, microphone frontend and playback route were
preserved. HA was independently restarted for an Echo Show deployment during
this work; no additional HA or Dot restart was requested for this package.

All 47 repository tests passed, including real HTTP signing/redirect tests
against a local test server and the observed brightness-scaled RGB regression.
The live card references 53 available entities. The final native-settings
comparison found only the explicitly selected feature changes.

Private receipts include the before/after native settings, USB-verified SSH
host identity, package hash, HA configuration check, template results,
dashboard readback and PBX registration. They contain local identifiers and
must not be committed. The public tests exercise service contracts, action
ownership, readiness/priority states and signed HTTP status requests.
