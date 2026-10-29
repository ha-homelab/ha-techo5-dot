# Native SIP phone on TECHO5 Dot

TECHO5 already has a SIP speakerphone in `echod`. Use its native Home Assistant
entities and actions with a separate PBX account for each Dot. No additional phone
daemon or custom HA integration is needed for the existing G.711 call path.

This guide describes the **v1.0.40** interface and source review. It is not evidence
of a successful registration or an audible call on a particular device. Keep
registration results and supervised call results separate in the dated
[deployment status](status.md).

## Compatibility and source pin

The reviewed Dot release tag is `dot-v1.0.40`, platform commit
[`e369da6`](https://github.com/HuskerMinion/techo5-dot/tree/e369da6fb320c79d027acf25acfab7c4ab8c4cd9),
and the shared-source snapshot used for this review is
[`2ae3c75`](https://github.com/HuskerMinion/techo5/tree/2ae3c75776eb04f614295ceba7de3cfcf60e531f).
That snapshot was taken after the release; it is **not a proven revision of the
shipped daemon binary**. The reviewed `phone/sip.go`, `phone/call.go`,
`phone/phone.go` and `mic/webrtc.go` are byte-identical to the pre-release snapshot
[`892cdef`](https://github.com/HuskerMinion/techo5/tree/892cdef6663acbb6ee963ed5862e363d61aff253).
The native action schema was also checked in HA against the running v1.0.40
devices. The platform and daemon have separate histories: moving `main`, a newer
release, and the original v1.0.34 preparation lock are not interchangeable pins.
The helper checks the target's advertised HA interface before writing, but that
check cannot establish acoustic quality.

The native account action takes exactly three strings: `server`, `username`,
`password`. `server` is a hostname, such as `pbx.example.net`, without a scheme,
port or SIP URI. The helper's `device_prefix` selects the existing HA actions and
entities; it is not a fourth argument to the firmware action.
[Native action schema](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/phone/phone.go#L802)

- **Default transport:** SIP over TLS on **5061**, with **SDES-SRTP** media. This is
  not DTLS-SRTP. The PBX certificate must match the configured hostname and chain
  to a CA trusted by the Dot's system trust store. The account action exposes no
  custom CA, certificate fingerprint or verification-bypass setting.
- **Explicit LAN alternative:** the native **Phone without encryption** switch
  selects UDP **5060** and unencrypted RTP. It is off by default. The provisioning
  helper preserves that switch; it never downgrades transport automatically. If
  this mode is deliberately selected for a trusted local PBX, change the switch
  separately while idle and verify the PBX mode matches. Changing it reloads the
  line and ends a current SIP call.
- **Audio:** G.711 **PCMU/ulaw or PCMA/alaw**, 8 kHz mono, 20 ms packets. Configure a
  matching PBX codec. The current phone path does not provide G.722 or Opus
  wideband calling, even though the microphone frontend runs at 16 kHz.
- **Account and line:** one account per device and one active native phone call.
  Give each Dot its own PBX username; do not reuse one registration across Dots.
- **HA link:** the Dot must already use its own encrypted ESPHome API key. The
  firmware refuses account credentials without that key.

[Transport implementation](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/phone/sip.go#L54)
and [codec defaults in the pinned Diago dependency](https://github.com/emiago/diago/blob/3ec6c2b20a3a08570dd446da05e5dcdeb6f02830/diago.go#L193).

## Provision through Home Assistant

Use [configure_phone.py](../scripts/configure_phone.py) with private files rather
than putting a password or HA token in shell arguments, an automation, or a
checked-in YAML file. The script configures an account; it does not place calls,
answer calls, start recordings or change wake-word and Sendspin settings.

Prepare a private copy of the [example account](../examples/phone-account.example.json):

```sh
umask 077
mkdir -p private/phone
cp examples/phone-account.example.json private/phone/account.json
chmod 600 private/phone/account.json
```

Edit that copy privately. Replace `device_prefix` with the target's existing
ESPHome action prefix, `server` with its PBX hostname, and both `REPLACE_WITH_PBX_*`
values with that device's credentials. Do not derive the prefix from a display
name that may have been renamed; inspect the available native actions in HA.

Also create `private/phone/ha-url.txt` containing the HA base URL and
`private/phone/ha-token.txt` containing a valid HA bearer token, one value per file.
Use owned, regular files with mode **0600**; **0400** is accepted for read-only
inputs. Symlinks and files readable by other users are refused. Keep the receipt
private as well, and do not publish these files or API request-body logs.

Run the read-only plan first:

```sh
python3 scripts/configure_phone.py \
  --config private/phone/account.json \
  --ha-url-file private/phone/ha-url.txt \
  --token-file private/phone/ha-token.txt \
  --receipt private/phone/receipt.json \
  --timeout 45
```

The default performs live read-only HA checks. It checks the account-action
schema, target entities and idle state before deciding whether an apply is
needed. It does not submit the credentials. After reviewing the plan, use the
same arguments with `--apply` to provision:

```sh
python3 scripts/configure_phone.py \
  --config private/phone/account.json \
  --ha-url-file private/phone/ha-url.txt \
  --token-file private/phone/ha-token.txt \
  --receipt private/phone/receipt.json \
  --timeout 45 \
  --apply
```

Prefer HTTPS for HA. `--allow-http-lan` is an explicit exception for an HTTP HA
endpoint on the trusted local network; it carries the token and SIP credentials
without HTTP-layer encryption. It does not change the separate SIP transport.
`--timeout 45` bounds the helper's verification wait; it is not a phone-call timer.

Applying an account reloads its SIP line. Keep the phone, voice satellite and
native speaker idle. The helper preserves existing settings and checks them
again afterwards. A successful apply requires a fresh native Phone observation
after the request and **Ready**, with no active peer, sustained for two seconds.
An unchanged old **Ready** value is insufficient. This confirms administrative
readiness, not either direction of audible media.

### Receipts and repeat runs

The private receipt records a successful verification and a keyed fingerprint
of the requested account and target, without storing the password itself. An
unchanged repeat with matching receipt and current healthy state can skip a
redundant account write. Before a new account POST it invalidates the previous
receipt, so an unverified replacement cannot leave that old success attestation
usable. The helper never automatically retries an account POST whose outcome
is ambiguous.

The device deliberately does not expose its stored SIP password through HA.
Consequently, **a receipt cannot detect an account changed outside this helper**.
Nor does **Ready** prove which hidden account is stored. Retain the private
account file as the desired configuration, check the PBX registration identity,
and invalidate a stale receipt before an intentional reconciliation. If a request
times out, inspect HA and the PBX before trying again: the first request may have
succeeded and another write would reload the line.

## Native controls and voice

Add the [phone control card](../examples/home-assistant/phone-controls.yaml) to a
dashboard's Manual card editor. Replace its four example IDs with the target's
existing entities: **Phone**, **Phone call**, **Answer call**, and **Hang up**.
Renamed registry IDs may differ from the example. The card has no dial action or
automatic answering, and does not create duplicate sensors or buttons.

The native action names are `esphome.echo_dot_example_phone_call` (`number`),
`esphome.echo_dot_example_phone_call_named` (`number`, `name`),
`esphome.echo_dot_example_phone_answer`, and
`esphome.echo_dot_example_phone_hangup`. Replace the prefix with the verified
target action prefix. Do not expose unrestricted destinations through an
automation. The Dot's physical action button answers a ringing call and hangs up
a dialing or connected call, independently of an HA voice round trip.
[Button behaviour](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/phone/phone.go#L363)

The built-in contact matcher recognizes English calling phrases. Adding a Russian
contact name does not teach it Russian commands such as a request to call that
contact. Russian calling, answering and hanging up need an explicit HA
conversation route with a bounded destination list and a verified source-device
mapping. HA's sentence trigger supplies `trigger.device_id`; current HA resolves
it from the originating satellite's device registry entry when available. Reject
requests with an absent or unrecognized source, and map known device IDs to
specific native actions or buttons. Do not construct an action from a slugified
device display name.
[Native matcher](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/voice/callask.go)
and [HA 2026.10.4 trigger source](https://github.com/home-assistant/core/blob/2026.10.4/homeassistant/components/conversation/trigger.py#L124).

**Wake word during calls** is off by default and is preserved by this workflow.
Even when enabled, far-end speech temporarily blocks wake activation; a configured
local hang-up word has similar restrictions. This guide does not install a voice
automation or change wake settings. Use the physical or HA button for the initial
acceptance tests.
[Wake and hang-up restrictions](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/docs/phone.md#L173)

## Audio path and remaining limits

`echod` owns one capture stream and the playback device. Dot 2 capture is card 0,
device 24: 16 kHz, packed 24-bit little-endian, seven microphones plus two playback
loopback channels. Its subscribers receive processed 16 kHz mono frames. The SIP
path downsamples these to G.711 at 8 kHz and simultaneously receives the far end;
playback ultimately runs at 48 kHz, 16-bit stereo on card 0, device 23. The speaker
arbiter suspends background media for the call and resumes it when the claim ends.
Announcements can temporarily take the call's local speaker. A second standalone
SIP daemon would need audio sharing and the same interruption policy, so it is not
a drop-in improvement.
[Capture](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/hardware/mic/device_dot.go#L10),
[call pipeline](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/phone/call.go#L25),
[speaker arbitration](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/hardware/speaker/driver.go#L274).

The built-in echo canceller uses the capture stream's aligned digital loopback.
It cannot fully predict loudspeaker distortion, and upstream documents residual
echo that leveling can amplify. The reviewed **Dot image lacks the WebRTC AEC
helper** offered by some other TECHO5 devices. Two-way transport is implemented;
clear double-talk at this installation's volume and distance still needs a
supervised listening test.
[AEC limitation](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/phone/call.go#L123),
[Dot helper availability](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/hardware/mic/webrtc.go#L60).

The native SIP path has bounded ringing and local hangup, but the reviewed code
has **no explicit RTP inactivity watchdog** and does not enable Diago's optional
RTP jitter buffer. It drops excess receive frames and drains playback backlog
above 300 ms. A lost media path must not be assumed to end the SIP call promptly.
The separate TECHO5 intercom has its own five-second inactivity timeout and
carries 16 kHz PCM over an encrypted HTTP-upgrade protocol; those properties do
not apply to SIP. [SIP receive path](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/phone/call.go#L235),
[intercom deadlines](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/phone/intercom.go#L151).

## Bounded acceptance on each Dot

Run these only in a supervised test window with people at both ends. Use dedicated
local test destinations with a **45-second absolute call limit enforced by the
PBX**. That limit is a prerequisite, not supplied by the card or provisioning
script. Keep external/PSTN routes out of the test. Do not auto-answer or record
audio. Stop on the first failure and do not proceed to another Dot.

1. Record the idle baseline: Phone state, empty peer, no active PBX call, existing
   wake model and threshold, Assist pipelines, native speaker state and Sendspin
   connection. Confirm the PBX registration belongs to the intended account.
2. Make one incoming call, answer with the physical action button, and end within
   **30 seconds**. Check both directions, a short pause for echo, and about five
   seconds of simultaneous speech. Hang up using the Dot's button.
3. Within **10 seconds**, require Phone **Ready**, empty peer and no PBX call.
   Then make one outgoing native call, manually answer at the other endpoint,
   and hang up there within **30 seconds**. Check the same recovery conditions.
4. Cancel one unanswered incoming ring after at most **10 seconds**. Confirm no
   stuck ringing or call state.
5. If music is already playing, make one further call of at most **30 seconds**
   and verify that it yields and resumes correctly. Otherwise mark music
   coexistence pending. Check wake operation and the saved settings afterwards.
6. Treat signaling-loss and media-loss behaviour as separate, supervised tests
   with the same PBX cap. If they have not been run, record them as pending; normal
   hangup does not establish recovery from a lost network path.

For every result distinguish registration, signaling, each audible direction,
echo/double-talk, hangup, and voice/music recovery. **Ready** alone completes only
the registration check. This setup has not been established as an emergency
calling service.
