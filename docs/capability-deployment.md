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

## Access that still requires the owner

Native web setup requires an actual Action-button press to admit the waiting
browser. This is separate from authorized SSH access. The signed Remote API
also requires a key created through that admitted session. The
[read-only API client](../scripts/remote_status.py) and protocol/transport tests
are provided, but a live signed API request is not considered verified without
that key. The setup and key steps are in the [access guide](capability-access.md).

Native house features need the same private house word on both devices.
Enabling nearest-answer switches alone does not establish this shared
credential. Until both are configured through admitted setup, authenticated
house arbitration, house settings sharing and direct house intercom remain
unverified. The existing PBX route is independent of that credential.

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

Private receipts include the before/after native settings, USB-verified SSH
host identity, package hash, HA configuration check, template results,
dashboard readback and PBX registration. They contain local identifiers and
must not be committed. The public tests exercise service contracts, action
ownership, readiness/priority states and signed HTTP status requests.
