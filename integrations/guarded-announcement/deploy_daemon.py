#!/usr/bin/env python3
"""Quiet manual daemon maintenance; no firmware, settings, keys or sound tests.

An expired watchdog restores the old on-disk binary without killing a live
process. A later idle maintenance restart may therefore be required.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import ssl
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

FLAGS = ("atomic_idle_guard", "dedup", "owned_cancel", "honest_completion", "deadline_enforced")
BASE = "/data/techo5-linux/myshka-maintenance"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_token(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid()
                or stat.S_IMODE(meta.st_mode) != 0o600 or meta.st_size > 4096):
            raise ValueError("HA token file must be owned, regular, mode 0600 and <=4096 bytes")
        value = os.read(fd, 4097).decode().strip()
        if not value or any(c.isspace() for c in value):
            raise ValueError("Invalid HA token file")
        return value
    finally:
        os.close(fd)


class HA:
    def __init__(self, origin, credential):
        self.url = urlsplit(origin)
        if (self.url.scheme not in {"http", "https"} or not self.url.hostname
                or self.url.username or self.url.password or self.url.path not in {"", "/"}
                or self.url.query or self.url.fragment):
            raise ValueError("HA URL must be a bare HTTP(S) origin")
        self.credential = credential

    def request(self, path, data=None):
        cls = http.client.HTTPSConnection if self.url.scheme == "https" else http.client.HTTPConnection
        kwargs = {"timeout": 10}
        if self.url.scheme == "https":
            kwargs["context"] = ssl.create_default_context()
        conn = cls(self.url.hostname, self.url.port, **kwargs)
        try:
            conn.request("POST" if data is not None else "GET", path,
                         None if data is None else json.dumps(data),
                         {"Authorization": "Bearer " + self.credential, "Content-Type": "application/json"})
            reply = conn.getresponse()
            if reply.status != 200:
                raise ValueError(f"HA request failed (HTTP {reply.status}); no redirect followed")
            raw = reply.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError("HA response too large")
            return json.loads(raw)
        finally:
            conn.close()

    def stable_idle(self, expected):
        for index in range(3):
            states = {item["entity_id"]: item["state"] for item in self.request("/api/states")}
            failed = [key for key, value in expected.items() if states.get(key) != value]
            if failed:
                raise ValueError("Idle check failed or entity missing: " + ", ".join(failed))
            if index < 2:
                time.sleep(1)


def ssh(args, command, data=None):
    cmd = ["ssh", "-i", str(args.identity), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
           "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=" + str(args.known_hosts),
           "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2",
           "root@" + args.host, command]
    result = subprocess.run(cmd, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if result.returncode:
        raise ValueError(f"SSH maintenance failed (exit {result.returncode}); inspect the job status")
    return result.stdout.decode().strip()


def invoke(args, job, mode):
    return ssh(args, "/bin/busybox.static sh " + shlex.quote(job + "/maintenance.sh")
               + " " + shlex.quote(job) + " " + mode
               + " " + args.old_sha256 + " " + args.new_sha256)


def expected_states(args):
    p = args.prefix
    expected = {f"assist_satellite.{p}_assist_satellite": "idle", f"media_player.{p}_speaker": "idle",
                f"sensor.{p}_phone": "Ready", f"sensor.{p}_phone_call": ""}
    extras = {}
    for value in args.idle_entity:
        entity, separator, state = value.partition("=")
        if not separator or not re.fullmatch(r"[a-z_]+\.[a-z0-9_]+", entity):
            raise ValueError("Idle entities must be ENTITY=STATE")
        if entity in expected or entity in extras:
            raise ValueError("Do not override or repeat an idle guard")
        extras[entity] = state
    if len(extras) < 3:
        raise ValueError("Supply the three verified general/alarm/timer sounding idle guards")
    expected.update(extras)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "apply", "ack", "status"))
    parser.add_argument("--host", required=True, help="device IP with an existing SSH host pin")
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path, required=True)
    parser.add_argument("--old-sha256", required=True)
    parser.add_argument("--new-sha256", required=True)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--ha-url")
    parser.add_argument("--ha-token-file", type=Path)
    parser.add_argument("--prefix", help="verified ESPHome entity prefix")
    parser.add_argument("--idle-entity", action="append", default=[], metavar="ENTITY=STATE")
    parser.add_argument("--job", help="job ID from apply, required for status/ack")
    args = parser.parse_args()
    address = ipaddress.ip_address(args.host)
    if address.is_multicast or address.is_unspecified:
        raise ValueError("Provide a unicast device IP")
    if not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in (args.old_sha256, args.new_sha256)):
        raise ValueError("Both exact SHA-256 hashes are required")
    if args.old_sha256 == args.new_sha256:
        raise ValueError("Old and new binary hashes must differ")
    if args.mode in {"status", "ack"} and not args.job:
        raise ValueError("A job ID is required")
    job_id = args.job or uuid.uuid4().hex
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("Invalid job ID")
    job = BASE + "/" + job_id
    if args.mode == "status":
        print(invoke(args, job, "status"))
        return
    if not (args.ha_url and args.ha_token_file and args.prefix
            and re.fullmatch(r"[a-z0-9_]+", args.prefix)):
        raise ValueError("HA origin, private token file and verified entity prefix are required")
    expected = expected_states(args)
    ha = HA(args.ha_url, read_token(args.ha_token_file))
    ha.stable_idle(expected)
    if args.mode == "check":
        print("HA idle guards passed; no device changes made")
        return
    if args.mode == "ack":
        request_id = "announce-" + uuid.uuid4().hex + "-000"
        result = ha.request(f"/api/services/esphome/{args.prefix}_guarded_announcement_capabilities?return_response",
                            {"request_id": request_id})
        response = result.get("service_response", {})
        if (response.get("request_id") != request_id or not response.get("boot_id")
                or response.get("protocol") != "cisco-announcement-v1"
                or any(response.get(flag) is not True for flag in FLAGS)):
            raise ValueError("Native capabilities did not confirm all five guarantees")
        ha.stable_idle(expected)
        invoke(args, job, "ack")
        print(json.dumps({"job": job_id, "status": "confirmed", "sha256": args.new_sha256}))
        return
    if not args.binary or digest(args.binary) != args.new_sha256:
        raise ValueError("Local binary does not match the explicit new SHA-256")
    ssh(args, "set -e; umask 077; /bin/busybox.static mkdir -p " + shlex.quote(BASE)
        + "; /bin/busybox.static mkdir " + shlex.quote(job))
    params = f"ID={job_id}\nOLD={args.old_sha256}\nNEW={args.new_sha256}\n"
    script = Path(__file__).with_name("maintenance.sh").read_bytes()
    for name, data in (("params", params.encode()), ("maintenance.sh", script),
                       ("echod.next", args.binary.read_bytes())):
        ssh(args, "umask 077; /bin/busybox.static cat > " + shlex.quote(job + "/" + name), data)
    ha.stable_idle(expected)
    print(json.dumps({"job": job_id, "status": "starting", "rollback_after_seconds": 180}), flush=True)
    invoke(args, job, "apply")
    print(json.dumps({"job": job_id, "status": "awaiting_health_ack",
                      "note": "Run ack within 160 seconds using the same parameters; no sound test."}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, http.client.HTTPException) as exc:
        print("Maintenance: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
