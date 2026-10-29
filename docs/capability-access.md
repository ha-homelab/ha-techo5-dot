# Administration and local media receivers

This guide extends the [TECHO5 v1.0.40 capability audit](capabilities.md).
Use it for an already converted Dot running the normal Linux image. It is not
a flashing procedure. Examples use `echo_dot_example`; obtain the real prefix
from the device's Home Assistant page.

## Supported SSH access

The native `switch.echo_dot_example_ssh` starts Dropbear on TCP port 22. The
supported login is `root` with an authorized public key; password logins are
disabled. There is no separate password in Home Assistant to look up.

Before enrolling a key, compare its fingerprint with the existing key list.
If the intended key already matches, enable SSH without rewriting any keys.
The action `esphome.echo_dot_example_ssh_keys`, with field `keys`, replaces the
**whole** authorized-key list. Preserve existing access when deliberately
adding a key, and never submit a private key.

Verify the SSH host-key fingerprint over an existing trusted administration
channel, such as the USB console, before accepting the network host key. Use a
dedicated known-hosts file and an explicit identity for repeatable maintenance:

```sh
ssh -i /path/to/private-key -o IdentitiesOnly=yes \
  -o PasswordAuthentication=no -o BatchMode=yes \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/path/to/verified-known-hosts \
  root@DEVICE_IP 'id; uptime'
```

Authorized keys and host keys live on persistent userdata. On the audited
image, `/root/.ssh` links to `/data/misc/echolocal/ssh`; host keys are under
`/data/techo5-linux/dropbear`. Ordinary packages and ad hoc system-file changes
need not survive an image update. Prefer native settings over a second daemon
or custom boot scripts.

No SFTP server was found in the audited image. If file transfer is necessary,
use legacy SCP (`scp -O`) or a bounded SSH stream. Turning the SSH switch off
closes the listener to new connections; existing sessions must be closed
separately. Telnet has no native toggle and adds no capability needed here.

## Setup page and its authorization

Enable `switch.echo_dot_example_setup_page`, then visit
`http://DEVICE_IP:8181/setup` on the local network. The waiting browser asks for
an Action-button press on the Dot. This admits that browser; merely enabling
the switch does not admit it. The request expires after 60 seconds.

The reviewed implementation closes the setup page after seven idle minutes,
or after one hour even if it remains active. Turn the switch off after use.
The absence of a listener after it closes is normal unless another enabled
feature also uses port 8181.

Some TECHO5 platforms with built-in Tailscale expose **Remote setup** and
**Let in from Home Assistant**. These entities were absent from the audited
Dot. Do not assume that instructions for a Show or Spot provide remote
admission on a Dot.

### House word for announcements and native intercom

On the verified v1.0.40 Dot setup page, open **Sound & Voice → Announcements**,
enter **House word**, and choose **Save**. Some help text still points to
Connections; the field is under Sound & Voice in this version.

Use the same private, hard-to-guess value of at least 16 characters on both
devices, including identical capitalization. Treat it as a shared credential
and keep it out of screenshots, logs and the public repository. This setting
authenticates announcements and native device-to-device intercom; the spoken
wake phrase is configured separately. An empty House word leaves these
incoming features disabled, and different values prevent the devices from
accepting each other's messages.

Enter it through the normally admitted setup session on each Dot. Changing
one device does not populate the other device's credential. This requirement
is separate from the account used for calls through a SIP/PBX server.

## Optional signed remote API

Home Assistant's encrypted ESPHome integration already controls the device.
The additional API is for a separate, defined local client, such as a status
collector. It is independent of SSH and of the setup browser session.

In an admitted setup session, open **Privacy & Security → Remote API** and
choose **Make a key**. Save the displayed key privately immediately. It is
shown once; making a new key invalidates the old one. Keep existing clients in
mind before rotating it. Enable `switch.echo_dot_example_remote_api` only when
the client has the key and is ready for verification.

The API uses `http://DEVICE_IP:8181/api/v1/`:

- `GET device` returns identity, software version and uptime.
- `GET entities` returns available settings, values, allowed ranges and whether
  each is writable.
- `POST entities/<id>` changes permitted everyday settings.
- `GET logs` streams bounded, redacted diagnostics; names can still be private.

Requests use an HMAC signature, timestamp and nonce in `X-Techo5-Remote`.
The allowed clock difference is 30 seconds, so synchronize client and device
time. Signing authenticates the request; HTTP does not encrypt its content.
Use the LAN or the existing home-network VPN. Do not publish this port to the
internet.

The API does not enable privacy features, SSH, recording, calling or itself,
and cannot install firmware, restart the device or run arbitrary HA actions.
Test with `GET device` and `GET entities` before considering writes. Turning
the native API switch off is the reversible way to stop the API without
discarding its credential.

The repository includes a deliberately read-only status client:

```sh
python3 scripts/remote_status.py http://DEVICE_IP:8181 \
  --key-file private/remote-api-key.txt --resource device
python3 scripts/remote_status.py http://DEVICE_IP:8181 \
  --key-file private/remote-api-key.txt --resource entities
```

Replace `DEVICE_IP` with the device's numeric address. The key file must be
owned by the calling user, a regular file, and mode `0600`. An existing
`TECHO5_REMOTE_KEY` environment variable is also supported; avoid placing
secrets in shell command history. The client cannot create a key, admit a
browser, enable the API or change settings. It refuses redirects and ignores
proxy environment variables. Results can contain private device names; keep
them out of public logs and repository commits. Tests cover the signing
protocol and local HTTP transport; a live check still needs an admitted key.

## AirPlay and DLNA without disturbing Assist

Keep Sendspin/Music Assistant as the main music route. Enable optional
receivers one at a time while no music or call is active, then verify their
listeners before a separate listening test.

**AirPlay:** `switch.echo_dot_example_airplay` enables the receiver.
`switch.echo_dot_example_airplay_2` only selects the preferred implementation;
its being on does not enable AirPlay by itself. Keep
`switch.echo_dot_example_airplay_sets_the_volume` at the intended existing
value so a sender does not unexpectedly change the device volume.

The reviewed implementation uses TCP 7000 for AirPlay 2 or TCP 5000 for the
classic fallback. Check the running `techo5-shairport-sync`/`techo5-nqptp`
processes and startup logs; the AirPlay 2 preference alone does not prove that
AirPlay 2 started. The native service manages the related firewall rules.
Discovery in a sender's output list verifies availability without selecting
the speaker or starting music.

**DLNA:** `switch.echo_dot_example_dlna` enables SSDP discovery and the HTTP
renderer. A read-only check is:

```sh
curl --fail --max-time 5 http://DEVICE_IP:8181/dlna/device.xml
```

The returned XML should identify a `MediaRenderer` with AVTransport,
RenderingControl and ConnectionManager services. Use the numeric device IP;
the reviewed handler rejects a hostname in the HTTP Host header. A successful
description fetch confirms the renderer endpoint, not that a particular
codec or track plays without interruptions. No playback is needed for this
check. The renderer advertises MP3, FLAC and WAV; seeking is not implemented
in the audited capability set.

Disable the corresponding native AirPlay/DLNA switch to roll back. Leaving
multiple receiver protocols available does not make the speaker a mixer:
the most recently started receiver takes playback ownership. Leave Bluetooth
phone audio off when passive BLE proxy use is the priority unless that
combination has been tested separately.

## Evidence and version boundaries

The on-device baseline was TECHO5 Dot v1.0.40, platform revision `e369da6`.
These implementation details were cross-checked against shared-source
revision `2ae3c75776eb04f614295ceba7de3cfcf60e531f`; that review pin is not a claim
that the installed binary was built from that exact shared-source revision.
Recheck behavior after updates.

- [SSH and key persistence](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/security/ssh.go)
- [Setup admission and expiry](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/setup/setup.go)
- [API key lifecycle](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/setup/remoteapi.go)
- [API request signing](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/remote/auth.go)
- [AirPlay receiver and fallback](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/streaming/airplay.go)
- [DLNA renderer](https://github.com/HuskerMinion/techo5/blob/2ae3c75776eb04f614295ceba7de3cfcf60e531f/echod/internal/feature/dlna/dlna.go)
