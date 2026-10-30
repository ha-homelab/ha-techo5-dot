#!/usr/bin/env python3
"""Configure a TECHO5 SIP account via HA; read-only dry-run is the default.

The configure() API accepts a transport whose request(method, path, payload=None,
timeout=...) returns JSON, retaining all guards. A receipt attests only to this
tool's last verified application: HA cannot read the stored account credentials.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import hmac
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
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASELINE = "v1.0.40"
OPTIONAL_ACTIONS = ("phone_call", "phone_call_named", "phone_contacts",
                    "intercom_call", "phone_answer", "phone_hangup")
SETTINGS_DOMAINS = {"select", "switch", "number", "text"}
UNAVAILABLE = {"unknown", "unavailable"}
IDLE_PHONE = {"Ready", "Not set up", "Login refused", "Cannot sign in"}
IDLE_PLAYER = {"idle", "off", "paused", "standby"}
READY_SETTLE = 2.0


class PhoneError(Exception):
    """A deliberately sanitized error safe to display without credentials."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _json(raw, label):
    try:
        return json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, TypeError):
        raise PhoneError(f"{label}: invalid JSON") from None


def private_read(path, label, missing_ok=False):
    """Read a bounded owner-only regular file without following a symlink."""
    fd = None
    try:
        before = os.lstat(path)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise PhoneError(f"{label}: a regular file without a symlink is required")
        if before.st_uid != os.getuid() or before.st_mode & 0o077:
            raise PhoneError(f"{label}: owner-only file permissions are required")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        current = os.fstat(fd)
        if ((before.st_dev, before.st_ino) != (current.st_dev, current.st_ino)
                or not stat.S_ISREG(current.st_mode)
                or current.st_uid != os.getuid() or current.st_mode & 0o077):
            raise PhoneError(f"{label}: file changed while opening")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise PhoneError(f"{label}: file is too large")
        return raw.decode("utf-8")
    except FileNotFoundError:
        if missing_ok:
            return None
        raise PhoneError(f"{label}: private file not found") from None
    except (OSError, UnicodeError):
        raise PhoneError(f"{label}: cannot read private file") from None
    finally:
        if fd is not None:
            os.close(fd)


def validate_config(value):
    expected = {"device_prefix", "server", "username", "password"}
    if type(value) is not dict or set(value) != expected:
        raise PhoneError("config: exactly device_prefix, server, username and password are required")
    if any(type(value[key]) is not str for key in expected):
        raise PhoneError("config: all fields must be strings")
    value = dict(value)
    for key in ("device_prefix", "server", "username"):
        value[key] = value[key].strip()
    if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", value["device_prefix"]) or len(value["device_prefix"]) > 100:
        raise PhoneError("config: invalid device prefix")
    host = value["server"]
    if (len(host) > 253 or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                              for label in host.rstrip(".").split("."))):
        raise PhoneError("config: server must be a hostname or IPv4 address without a port")
    if re.fullmatch(r"[0-9.]+", host):
        try:
            ipaddress.IPv4Address(host)
        except ValueError:
            raise PhoneError("config: invalid server address") from None
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,128}", value["username"]):
        raise PhoneError("config: invalid SIP username")
    if not value["password"] or len(value["password"]) > 1024 or any(c in value["password"] for c in "\r\n\0"):
        raise PhoneError("config: invalid SIP password")
    return value


def validate_url(value, allow_http_lan=False):
    try:
        if type(value) is not str or any(ord(c) < 33 for c in value.strip()):
            raise ValueError
        parsed = urllib.parse.urlsplit(value.strip())
        if (parsed.scheme not in {"https", "http"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError
        port, host = parsed.port, parsed.hostname
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host.lower() == "localhost"
        if parsed.scheme == "http" and not loopback and not allow_http_lan:
            raise PhoneError("URL: non-loopback HTTP requires --allow-http-lan")
        authority = f"[{host}]" if ":" in host else host.lower()
        if port is not None:
            authority += f":{port}"
        return f"{parsed.scheme}://{authority}"
    except (ValueError, TypeError):
        raise PhoneError("URL: an HTTP(S) origin without credentials, path, query or fragment is required") from None


def validate_token(value):
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._~+/-]+={0,2}", value) or len(value) > 16384:
        raise PhoneError("token: invalid bearer token")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPTransport:
    """No redirects, environment proxies, TLS bypasses, response logs or retries."""

    def __init__(self, url, token, allow_http_lan=False):
        self.url = validate_url(url, allow_http_lan)
        self.token = validate_token(token)
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def request(self, method, path, payload=None, timeout=10):
        if method not in {"GET", "POST"} or not path.startswith("/api/") or any(c in path for c in "?#\r\n"):
            raise PhoneError("HA request rejected")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.url + path, data=body, method=method,
                                         headers={"Authorization": "Bearer " + self.token,
                                                  "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=timeout) as response:
                if response.geturl() != self.url + path or not 200 <= response.status < 300:
                    raise PhoneError("HA response rejected")
                raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise PhoneError("HA response too large")
            return _json(raw, "HA response") if raw else None
        except urllib.error.HTTPError as error:
            error.close()
            raise PhoneError("HA request failed; HTTP error or redirect refused") from None
        except (OSError, ValueError):
            raise PhoneError("HA request failed; connection or TLS error") from None


def _request(transport, method, path, payload=None, timeout=10):
    try:
        return transport.request(method, path, payload=payload, timeout=timeout)
    except Exception:
        # Injected transports may include secrets in exception messages.
        raise PhoneError("HA request failed; no response details are displayed") from None


def check_services(value, prefix):
    if type(value) is not list:
        raise PhoneError("HA services: unexpected schema")
    domains = [item for item in value if type(item) is dict and item.get("domain") == "esphome"]
    if len(domains) != 1 or type(domains[0].get("services")) is not dict:
        raise PhoneError("HA services: ESPHome domain missing or ambiguous")
    services = domains[0]["services"]
    account = services.get(prefix + "_phone_account", {})
    fields = account.get("fields") if type(account) is dict else None
    if type(fields) is not dict or set(fields) != {"server", "username", "password"}:
        raise PhoneError("HA services: phone_account fields differ from the verified schema")
    for field in fields.values():
        if (type(field) is not dict or field.get("required") is not True
                or type(field.get("selector")) is not dict
                or set(field["selector"]) != {"text"}
                or (field["selector"]["text"] is not None and type(field["selector"]["text"]) is not dict)):
            raise PhoneError("HA services: phone_account requires three required text fields")
    return {name: prefix + "_" + name in services for name in OPTIONAL_ACTIONS}


def state_map(value):
    if type(value) is not list:
        raise PhoneError("HA states: unexpected schema")
    result = {}
    for item in value:
        if (type(item) is not dict or type(item.get("entity_id")) is not str
                or type(item.get("state")) is not str or type(item.get("attributes")) is not dict
                or item["entity_id"] in result):
            raise PhoneError("HA states: invalid or duplicate entity")
        result[item["entity_id"]] = item
    return result


def resolve_entities(states, prefix):
    # Exact native names: never infer a Music Assistant player from a loose match.
    result = {
        "firmware": f"update.{prefix}_firmware",
        "phone": f"sensor.{prefix}_phone",
        "peer": f"sensor.{prefix}_phone_call",
        "player": f"media_player.{prefix}_speaker",
        "satellite": f"assist_satellite.{prefix}_assist_satellite",
    }
    if any(entity not in states for entity in result.values()):
        raise PhoneError("HA states: a required native device entity is missing")
    return result


def check_device(states, entities, waiting=False, fresh=True):
    try:
        current = {role: states[entity] for role, entity in entities.items()}
    except KeyError:
        raise PhoneError("HA states: a required device entity disappeared") from None
    if any(item["state"].lower() in UNAVAILABLE for item in current.values()):
        raise PhoneError("Device unavailable; no further configuration attempted")
    firmware = current["firmware"]
    if (firmware["attributes"].get("installed_version") not in {BASELINE, BASELINE[1:]}
            or firmware["attributes"].get("in_progress", False)):
        raise PhoneError("Device firmware differs from idle v1.0.40 baseline")
    if (current["peer"]["state"] != "" or current["player"]["state"].lower() not in IDLE_PLAYER
            or current["satellite"]["state"].lower() != "idle"):
        raise PhoneError("Device busy; no further configuration attempted")
    phone = current["phone"]["state"]
    if waiting and fresh and phone == "Login refused":
        raise PhoneError("SIP login refused; no success receipt saved")
    if waiting and fresh and phone == "Cannot sign in":
        raise PhoneError("SIP registration failed; no success receipt saved")
    if phone not in IDLE_PHONE | ({"Connecting"} if waiting else set()):
        raise PhoneError("Phone busy or not in a recognized idle state")
    return phone == "Ready"


def settings_snapshot(states, prefix):
    result = {}
    for entity, item in states.items():
        domain, _, name = entity.partition(".")
        if domain in SETTINGS_DOMAINS and (name == prefix or name.startswith(prefix + "_")):
            if item["state"].lower() in UNAVAILABLE:
                raise PhoneError("Device settings unavailable; preservation cannot be verified")
            result[entity] = item["state"]
    if not result:
        raise PhoneError("Device settings missing; preservation cannot be verified")
    return result


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _fingerprint(config, url, key):
    return hmac.new(key, _canonical({"account": config, "ha_origin": url}), hashlib.sha256).hexdigest()


def load_receipt(path):
    raw = private_read(path, "receipt", missing_ok=True)
    if raw is None:
        return None
    value = _json(raw, "receipt")
    try:
        if (type(value) is not dict or value.get("schema_version") != 1
                or value.get("status") != "verified" or value.get("firmware") != BASELINE
                or not re.fullmatch(r"[0-9a-f]{64}", value["configuration_hmac_sha256"])
                or value["settings_before_sha256"] != value["settings_after_sha256"]
                or not re.fullmatch(r"[0-9a-f]{64}", value["settings_before_sha256"])):
            raise ValueError
        key = base64.b64decode(value["fingerprint_key"], validate=True)
        if len(key) != 32:
            raise ValueError
    except (KeyError, ValueError, TypeError):
        raise PhoneError("receipt: unsupported or invalid success receipt") from None
    return value


def save_receipt(path, value):
    path = Path(path)
    temporary = None
    try:
        private_read(path, "receipt", missing_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".phone-receipt-", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    except OSError:
        raise PhoneError("Account became Ready but saving the private receipt failed") from None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def invalidate_receipt(path):
    # A failed/ambiguous request may still replace the account. An older success
    # receipt must not subsequently attest to the wrong account.
    if private_read(path, "receipt", missing_ok=True) is not None:
        try:
            os.unlink(path)
        except OSError:
            raise PhoneError("Cannot invalidate previous receipt; nothing applied") from None


def receipt_parent(path):
    parent = Path(path).parent
    if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
        raise PhoneError("Receipt parent directory must exist and be writable")


def phone_refreshed(before, after):
    if before["state"] != after["state"]:
        return True
    old, new = before.get("last_updated"), after.get("last_updated")
    try:
        old = datetime.fromisoformat(old.replace("Z", "+00:00"))
        new = datetime.fromisoformat(new.replace("Z", "+00:00"))
        return old.tzinfo is not None and new.tzinfo is not None and new > old
    except (TypeError, ValueError, AttributeError):
        return False


def configure(config, ha_url, receipt_path, transport, *, apply=False,
              allow_http_lan=False, timeout=45.0, poll_interval=1.0,
              clock=time.monotonic, sleep=time.sleep):
    """Guarded API; transports must honor per-request timeout seconds.

    The report omits account values, entity IDs, URLs and paths. The only mutation
    is phone_account; transport switches and every other setting are preserved.
    """
    config = validate_config(config)
    ha_url = validate_url(ha_url, allow_http_lan)
    if (not math.isfinite(timeout) or not READY_SETTLE < timeout <= 300
            or not math.isfinite(poll_interval) or not 0.1 <= poll_interval <= 5):
        raise PhoneError("Readiness timeout/poll interval outside supported bounds")
    receipt = load_receipt(receipt_path)
    receipt_parent(receipt_path)
    optional = check_services(_request(transport, "GET", "/api/services"), config["device_prefix"])
    states = state_map(_request(transport, "GET", "/api/states"))
    entities = resolve_entities(states, config["device_prefix"])
    ready = check_device(states, entities)
    before = settings_snapshot(states, config["device_prefix"])
    matching = bool(receipt and hmac.compare_digest(
        receipt["configuration_hmac_sha256"],
        _fingerprint(config, ha_url, base64.b64decode(receipt["fingerprint_key"]))
    ))
    summary = {"firmware": BASELINE, "settings_checked": len(before), "optional_actions": optional}
    if matching and ready:
        return dict(summary, status="already_verified", receipt_scope="last application by this tool only")
    if not apply:
        return dict(summary, status="dry_run", account_change="would_apply")
    states = state_map(_request(transport, "GET", "/api/states"))
    check_device(states, entities)
    if settings_snapshot(states, config["device_prefix"]) != before:
        raise PhoneError("Device settings changed during preflight; nothing applied")
    previous_phone = states[entities["phone"]]
    payload = {key: config[key] for key in ("server", "username", "password")}
    invalidate_receipt(receipt_path)
    _request(transport, "POST", "/api/services/esphome/" + config["device_prefix"] + "_phone_account", payload)
    deadline = clock() + timeout
    ready_since = None
    fresh = False
    while clock() < deadline:
        states = state_map(_request(transport, "GET", "/api/states", timeout=min(10, deadline - clock())))
        after = settings_snapshot(states, config["device_prefix"])
        if after != before:
            raise PhoneError("Device settings changed after account request; no success receipt saved")
        current_phone = states.get(entities["phone"])
        if current_phone is None:
            raise PhoneError("HA states: phone entity disappeared after account request")
        fresh = fresh or phone_refreshed(previous_phone, current_phone)
        ready = check_device(states, entities, waiting=True, fresh=fresh) and fresh
        now = clock()
        if now >= deadline:
            break
        if not ready:
            ready_since = None
        elif ready_since is None:
            ready_since = now
        if ready_since is not None and now - ready_since >= READY_SETTLE:
            key = secrets.token_bytes(32)
            digest = hashlib.sha256(_canonical(before)).hexdigest()
            save_receipt(receipt_path, {
                "schema_version": 1, "status": "verified", "firmware": BASELINE,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "fingerprint_key": base64.b64encode(key).decode("ascii"),
                "configuration_hmac_sha256": _fingerprint(config, ha_url, key),
                "settings_before_sha256": digest, "settings_after_sha256": digest,
                "settings_checked": len(before),
                "scope": "last application by this tool; external SIP credential changes cannot be read back",
            })
            return dict(summary, status="verified", settings_preserved=True)
        sleep(min(poll_interval, max(0, deadline - clock())))
    raise PhoneError("SIP readiness timed out; accepted account request is not verified success")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes bad arguments, including accidental secrets.
        self.exit(2, "Invalid command line; use --help. Values are not displayed.\n")


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--ha-url-file", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Apply after preflight; otherwise only read HA")
    parser.add_argument("--allow-http-lan", action="store_true", help="Explicitly permit plaintext HTTP to trusted LAN HA")
    parser.add_argument("--timeout", type=float, default=45.0, help="Readiness deadline in seconds (greater than 2, at most 300)")
    args = parser.parse_args(argv)
    try:
        inputs = (args.config, args.ha_url_file, args.token_file)
        if any(args.receipt.resolve() == item.resolve() for item in inputs):
            raise PhoneError("Receipt must not overwrite an input file")
        config = validate_config(_json(private_read(args.config, "config"), "config"))
        url = validate_url(private_read(args.ha_url_file, "URL"), args.allow_http_lan)
        token = validate_token(private_read(args.token_file, "token"))
        result = configure(config, url, args.receipt, HTTPTransport(url, token, args.allow_http_lan),
                           apply=args.apply, allow_http_lan=args.allow_http_lan, timeout=args.timeout)
        print(json.dumps(result, sort_keys=True))
        return 0
    except PhoneError as error:
        print(f"Configuration failed: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError):
        print("Configuration failed; input or local I/O error. Values are not displayed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
