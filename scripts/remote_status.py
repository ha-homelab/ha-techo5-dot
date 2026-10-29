#!/usr/bin/env python3
"""Read TECHO5 device status with an already admitted Remote API key.

Only GET /api/v1/device and GET /api/v1/entities are supported. This client
cannot enable the API, admit a browser, create a key, or change a device.
The key comes from --key-file (owned regular file, mode 0600) or, when that
option is absent, TECHO5_REMOTE_KEY. No credentials are written to disk.

Signing follows the upstream remote/auth.go protocol at revision
2ae3c75776eb04f614295ceba7de3cfcf60e531f: timestamp in seconds, a fresh 12-byte
nonce, an HMAC-derived secret, and the trailing newline in the signed message.
HTTP authenticates requests but does not encrypt returned entity states. Use
only the intended device on a trusted network. DNS names and proxies are not
used; provide an explicit IP address and port if needed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import hmac
import http.client
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import secrets
import ssl
import stat
import sys
import time
from urllib.parse import urlsplit


RESOURCES = {"device": "/api/v1/device", "entities": "/api/v1/entities"}
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
KEY_ENV = "TECHO5_REMOTE_KEY"


class RemoteStatusError(Exception):
    """An error safe to display without credentials or response bodies."""


@dataclass(frozen=True)
class Target:
    scheme: str
    host: str
    port: int


def validate_target(value: str) -> Target:
    """Accept only a bare HTTP(S) origin with a canonical unicast IP literal."""
    if not value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        raise RemoteStatusError("Target must be a bare HTTP(S) origin with an IP address.")
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment or "?" in value or "#" in value
                or parsed.username is not None or parsed.password is not None
                or not parsed.hostname or "%" in parsed.netloc):
            raise ValueError
        address = ipaddress.ip_address(parsed.hostname)
        if address.is_multicast or address.is_unspecified:
            raise ValueError
        host = str(address)
        authority = f"[{host}]" if address.version == 6 else host
        port = parsed.port
        if parsed.netloc != authority + (f":{port}" if port is not None else ""):
            raise ValueError
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
        return Target(parsed.scheme, host, port or (443 if parsed.scheme == "https" else 80))
    except (TypeError, ValueError):
        raise RemoteStatusError("Target must be a bare HTTP(S) origin with a canonical IP address.") from None


def validate_key(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[0-9a-f]{48}", value):
        raise RemoteStatusError("Remote API key must be the 48-character key shown by the device.")
    return value


def load_key(path: Path | None) -> str:
    if path is None:
        value = os.environ.get(KEY_ENV)
        if value is None:
            raise RemoteStatusError("Supply --key-file or set TECHO5_REMOTE_KEY privately.")
        return validate_key(value)
    descriptor = None
    try:
        # Validate the descriptor, not an earlier pathname stat; refuse symlinks
        # and avoid blocking on a FIFO before discovering that it is not a file.
        if not hasattr(os, "O_NOFOLLOW"):
            raise RemoteStatusError("This platform cannot safely open the private key file.")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_size > 128):
            raise RemoteStatusError("Key file must be owned by you, regular, mode 0600, and at most 128 bytes.")
        value = os.read(descriptor, 129)
        if len(value) > 128:
            raise RemoteStatusError("Key file exceeds the size limit.")
        return validate_key(value.decode("ascii"))
    except (OSError, UnicodeError):
        raise RemoteStatusError("Cannot read the private key file safely.") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def signature(key: str, path: str, *, timestamp: int | None = None,
              nonce: str | None = None) -> str:
    """Sign one of the two supported GET paths; never sign arbitrary actions."""
    key = validate_key(key)
    if path not in RESOURCES.values():
        raise RemoteStatusError("Only device and entities status reads are supported.")
    timestamp = int(time.time()) if timestamp is None else timestamp
    nonce = secrets.token_hex(12) if nonce is None else nonce
    if type(timestamp) is not int or timestamp < 0 or not re.fullmatch(r"[0-9a-f]{24}", nonce):
        raise RemoteStatusError("Invalid signing timestamp or nonce.")
    derived = hmac.new(b"techo5-remote v1", key.encode(), hashlib.sha256).digest()
    message = "\n".join(("v1", "GET", path, str(timestamp), nonce,
                           hashlib.sha256(b"").hexdigest())) + "\n"
    digest = hmac.new(derived, message.encode(), hashlib.sha256).hexdigest()
    return f"v1 {timestamp} {nonce} {digest}"


def fetch_status(origin: str, resource: str, key: str, *, timeout: float = 10) -> dict | list:
    target = validate_target(origin)
    if resource not in RESOURCES:
        raise RemoteStatusError("Only device and entities status reads are supported.")
    if not math.isfinite(timeout) or not 1 <= timeout <= 30:
        raise RemoteStatusError("Timeout must be between 1 and 30 seconds.")
    path = RESOURCES[resource]
    header = signature(key, path)
    if target.scheme == "https":
        connection = http.client.HTTPSConnection(target.host, target.port, timeout=timeout,
                                                 context=ssl.create_default_context())
    else:
        connection = http.client.HTTPConnection(target.host, target.port, timeout=timeout)
    try:
        # http.client neither follows redirects nor reads proxy environment
        # variables. Never retry a signed request or print its headers/body.
        connection.request("GET", path, headers={"X-Techo5-Remote": header,
                                                 "Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            if 300 <= response.status < 400:
                raise RemoteStatusError("Device returned a redirect; it was not followed.")
            if response.status == 401:
                raise RemoteStatusError("Authentication failed; verify the admitted key and both clocks (30-second tolerance).")
            if response.status == 429:
                raise RemoteStatusError("Device rate limit reached; wait at least one minute before trying again.")
            raise RemoteStatusError(f"Device status request failed (HTTP {response.status}).")
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise RemoteStatusError("Device did not return JSON status.")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RemoteStatusError("Device response exceeds the size limit.")
        data = json.loads(raw)
        if not isinstance(data, dict if resource == "device" else list):
            raise RemoteStatusError("Device returned an unexpected status structure.")
        return data
    except (OSError, http.client.HTTPException, ValueError, UnicodeError):
        raise RemoteStatusError("Could not read valid device status; check connectivity and the API configuration.") from None
    finally:
        connection.close()


class QuietParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes invalid arguments, which may include an
        # accidentally pasted credential. Help lists the supported arguments.
        raise RemoteStatusError("Invalid arguments; use --help for accepted options.")


def main(argv=None) -> int:
    parser = QuietParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("origin", help="bare HTTP(S) URL containing the device IP, optionally :port")
    parser.add_argument("--resource", choices=RESOURCES, default="device")
    parser.add_argument("--key-file", type=Path, help="owned mode-0600 file; otherwise use TECHO5_REMOTE_KEY")
    parser.add_argument("--timeout", type=float, default=10, help="socket timeout, 1–30 seconds (default: 10)")
    try:
        args = parser.parse_args(argv)
        validate_target(args.origin)
        data = fetch_status(args.origin, args.resource, load_key(args.key_file), timeout=args.timeout)
        print(json.dumps(data, ensure_ascii=True, indent=2))
        return 0
    except RemoteStatusError as error:
        print(f"Remote status: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
