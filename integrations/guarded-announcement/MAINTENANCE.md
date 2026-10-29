# Quiet daemon maintenance

`deploy_daemon.py` is an operator tool for an already configured TECHO5 Linux
Dot with working SSH administration. It replaces `/usr/local/bin/echod` in the
currently active writable slot. It does not flash a system image, change the
active slot, reboot, change any key, or play test audio. The existing init
supervisor restarts the daemon after one controlled SIGTERM.

This is an experimental manual daemon patch, **not a signed upstream OTA**.
Keep the original compiled-in update trust key. A later official update can
replace this patch; announcement callers must check capabilities and fail
closed if the five required guarantees disappear.

## Before applying

1. Arrange an idle maintenance window: this restarts the service shared by
   voice, music and calls. Stop if someone is using it.
2. Build and test the exact source overlay. Keep its build record and SHA-256.
   Verify the old installed binary hash independently against the known release.
3. Use an existing SSH private key and known-host file. The helper requires strict
   host verification and never copies the key to a device.
4. Read the current HA entity registry. Verify the satellite, speaker, phone and
   phone-call entity names, plus all three sounding entities for that Dot. Missing
   entities fail closed. The defaults assume the entity names used by this repo.
5. Put an existing HA access token in an owned mode-0600 local file. The helper
   never copies it to the device. Use the existing authenticated HTTPS HA origin
   or a trusted local connection; redirects are refused.

Run one device at a time. A command has this shape; replace every placeholder:

```sh
python3 integrations/guarded-announcement/deploy_daemon.py apply \
  --host DEVICE_IP --identity /path/to/existing_private_key \
  --known-hosts /path/to/existing_known_hosts \
  --old-sha256 VERIFIED_OLD_SHA256 --new-sha256 BUILT_NEW_SHA256 \
  --binary /path/to/built/echod \
  --ha-url https://YOUR_HA_ORIGIN --ha-token-file /private/ha-token \
  --prefix VERIFIED_ENTITY_PREFIX \
  --idle-entity binary_sensor.VERIFIED_GENERAL_SOUNDING=off \
  --idle-entity binary_sensor.VERIFIED_ALARM_SOUNDING=off \
  --idle-entity binary_sensor.VERIFIED_TIMER_SOUNDING=off
```

`check` performs only the HA idle checks. `apply` checks three consecutive HA
snapshots before upload and again after upload. These are operational idle
checks, not an atomic device quiescence transaction: an unexpected user action
between the last snapshot and SIGTERM can still be interrupted. Do not deploy
during active use.

## Confirmation and rollback

The helper prints a job ID. After the daemon reconnects, run the same command
with `ack --job JOB_ID` instead of `apply`; `--binary` is no longer needed. ACK
must finish within 160 seconds of the maintenance start. It requires:

- Three stable idle snapshots, the response-only native capabilities action,
  and three more stable idle snapshots.
- The expected request ID, protocol, boot ID and all five capability flags.
- Both the on-disk binary and the running process matching the new hash.
- No maintenance hold remaining.

ACK does not submit an announcement, start media, open microphones or place a
call. Acoustic acceptance remains separate.

The detached watchdog expires after 180 seconds. Without ACK it atomically
restores the old **file**, releases only its own maintenance hold, and leaves
another operator's hold untouched. It refuses to overwrite an unexpected
third-party binary. The watchdog never kills a live process, because the user
may have started a real call. `rollback_staged_restart_required` therefore means
the old binary is restored but the new process is still running. Arrange another
idle window before a controlled restart. `rollback_file_restored` confirms the
file only; it does not claim the old service is healthy.

`status --job JOB_ID` uses only SSH and reports this distinction and the current
binary hash. Keep the SSH and hash arguments; HA arguments are unnecessary.

Maintenance files live under `/data/techo5-linux/myshka-maintenance/JOB_ID/`.
Successful ACK or rollback removes the staged new binary and retains the single
old `echod.previous` binary and small job records. No Alexa partitions, factory
images, audio recordings, or account backups are collected. After a later
successful maintenance cycle, remove obsolete job directories deliberately;
never remove the current unconfirmed job or another operator's maintenance hold.

Run the offline checks with:

```sh
python3 integrations/guarded-announcement/test_maintenance.py
sh -n integrations/guarded-announcement/maintenance.sh
```

These tests simulate rollback paths in a temporary directory and verify that a
running process is never killed, foreign holds and unexpected binaries survive,
bad backups are rejected, and absent idle entities fail closed. They do not
certify a device's network, power supply or acoustic output.
