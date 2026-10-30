import copy
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
from unittest.mock import patch
from scripts import configure_phone as phone

CONFIG = {"device_prefix": "example_dot", "server": "pbx.example.test",
          "username": "4101", "password": "example-password"}
URL = "https://ha.example.test"


def services():
    fields = {name: {"required": True, "selector": {"text": None}}
              for name in ("server", "username", "password")}
    return [{"domain": "esphome", "services": {
        "example_dot_phone_account": {"fields": fields},
        "example_dot_phone_hangup": {"fields": {}},
    }}]


def states(status="Not set up", stamp="2026-01-01T00:00:00+00:00"):
    def item(entity, state, **attributes):
        return {"entity_id": entity, "state": state, "attributes": attributes,
                "last_updated": stamp}
    return [
        item("update.example_dot_firmware", "off", installed_version="v1.0.40", in_progress=False),
        item("sensor.example_dot_phone", status),
        item("sensor.example_dot_phone_call", ""),
        item("media_player.example_dot_speaker", "idle"),
        item("assist_satellite.example_dot_assist_satellite", "idle"),
        item("switch.example_dot_phone_without_encryption", "off"),
        item("select.example_dot_wake_word", "example wake word"),
        item("number.example_dot_volume", "45"),
        item("text.example_dot_music_server", "music.example.test"),
        item("switch.another_device_option", "unavailable"),
    ]


def altered(items, entity, state):
    items = copy.deepcopy(items)
    next(item for item in items if item["entity_id"] == entity)["state"] = state
    return items


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Transport:
    def __init__(self, plan=None):
        self.plan = list(plan or [states()])
        self.services = services()
        self.calls = []
        self.post_error = None

    def request(self, method, path, payload=None, timeout=10):
        self.calls.append((method, path, copy.deepcopy(payload), timeout))
        if method == "POST":
            if self.post_error:
                raise self.post_error
            return []
        if path == "/api/services":
            return copy.deepcopy(self.services)
        if path == "/api/states":
            result = self.plan[0]
            if len(self.plan) > 1:
                self.plan.pop(0)
            return copy.deepcopy(result)
        raise AssertionError("unexpected test request")

    @property
    def posts(self):
        return [call for call in self.calls if call[0] == "POST"]


class ConfigurePhoneTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.receipt = self.root / "receipt.json"
        self.clock = Clock()

    def run_config(self, transport, **kwargs):
        return phone.configure(kwargs.pop("config", CONFIG), kwargs.pop("url", URL),
                               self.receipt, transport, clock=self.clock,
                               sleep=self.clock.sleep, **kwargs)

    def successful(self):
        transport = Transport([states(), states(), states("Connecting"), states("Ready")])
        result = self.run_config(transport, apply=True)
        self.assertEqual(result["status"], "verified")
        return transport

    def test_dry_run_performs_no_mutation_or_local_write(self):
        transport = Transport()
        before = list(self.root.iterdir())
        report = self.run_config(transport)
        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["settings_checked"], 4)
        self.assertTrue(report["optional_actions"]["phone_hangup"])
        self.assertFalse(report["optional_actions"]["phone_call"])
        self.assertEqual(transport.posts, [])
        self.assertEqual(list(self.root.iterdir()), before)

    def test_success_requires_readiness_and_preserves_settings(self):
        transport = self.successful()
        self.assertEqual(len(transport.posts), 1)
        self.assertEqual(transport.posts[0][1], "/api/services/esphome/example_dot_phone_account")
        self.assertEqual(transport.posts[0][2], {key: CONFIG[key] for key in ("server", "username", "password")})
        self.assertGreaterEqual(self.clock.now, 3)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(self.receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual(receipt["settings_before_sha256"], receipt["settings_after_sha256"])
        self.assertNotIn(CONFIG["password"], self.receipt.read_text())
        self.assertNotIn(URL, self.receipt.read_text())

    def test_matching_receipt_ready_is_idempotent_even_with_apply(self):
        self.successful()
        before = self.receipt.read_bytes()
        transport = Transport([states("Ready")])
        self.assertEqual(self.run_config(transport, apply=True)["status"], "already_verified")
        self.assertFalse(transport.posts)
        self.assertEqual(self.receipt.read_bytes(), before)

    def test_ready_without_receipt_does_not_claim_account_identity(self):
        self.assertEqual(self.run_config(Transport([states("Ready")]))["status"], "dry_run")

    def test_ambiguous_post_invalidates_old_receipt_and_never_retries(self):
        self.successful()
        transport = Transport([states("Ready")])
        transport.post_error = TimeoutError("response includes example-password")
        with self.assertRaises(phone.PhoneError) as caught:
            self.run_config(transport, apply=True, config=dict(CONFIG, password="test_different_password"))
        self.assertNotIn("example-password", str(caught.exception))
        self.assertEqual(len(transport.posts), 1)
        self.assertFalse(self.receipt.exists())
        again = Transport([states("Ready"), states("Ready"), states("Connecting"), states("Ready")])
        self.run_config(again, apply=True)
        self.assertEqual(len(again.posts), 1)

    def test_accepted_post_without_ready_times_out_without_receipt(self):
        transport = Transport([states(), states(), states("Connecting")])
        with self.assertRaisesRegex(phone.PhoneError, "timed out"):
            self.run_config(transport, apply=True, timeout=4)
        self.assertEqual(len(transport.posts), 1)
        self.assertFalse(self.receipt.exists())
        self.assertEqual(self.clock.now, 4)

    def test_old_ready_does_not_verify_new_account(self):
        with self.assertRaisesRegex(phone.PhoneError, "timed out"):
            self.run_config(Transport([states("Ready")]), apply=True, timeout=4)
        self.assertFalse(self.receipt.exists())

    def test_newer_ready_timestamp_verifies_without_catching_connecting(self):
        transport = Transport([states("Ready"), states("Ready"),
                               states("Ready", stamp="2026-01-01T00:00:05+00:00")])
        self.assertEqual(self.run_config(transport, apply=True)["status"], "verified")

    def test_stale_login_refusal_is_ignored_until_fresh_phone_observation(self):
        transport = Transport([states("Login refused"), states("Login refused"),
                               states("Login refused"), states("Ready")])
        self.assertEqual(self.run_config(transport, apply=True)["status"], "verified")

    def test_fresh_login_refusal_is_not_success(self):
        transport = Transport([states(), states(), states("Login refused")])
        with self.assertRaisesRegex(phone.PhoneError, "login refused"):
            self.run_config(transport, apply=True)
        self.assertFalse(self.receipt.exists())

    def test_cannot_sign_in_can_be_corrected_but_fresh_failure_is_rejected(self):
        transport = Transport([states("Cannot sign in"), states("Cannot sign in"),
                               states("Cannot sign in"), states("Ready")])
        self.assertEqual(self.run_config(transport, apply=True)["status"], "verified")
        self.receipt.unlink()
        failed = Transport([states(), states(), states("Cannot sign in")])
        with self.assertRaisesRegex(phone.PhoneError, "registration failed"):
            self.run_config(failed, apply=True)
        self.assertFalse(self.receipt.exists())

    def test_required_entity_disappearing_after_post_is_sanitized_failure(self):
        transport = Transport([states(), states(), [row for row in states("Ready")
                                                   if row["entity_id"] != "sensor.example_dot_phone"]])
        with self.assertRaisesRegex(phone.PhoneError, "phone entity disappeared"):
            self.run_config(transport, apply=True)
        self.assertFalse(self.receipt.exists())

    def test_schema_drift_refuses_before_post(self):
        for change in ("extra", "missing", "optional", "not_text"):
            with self.subTest(change=change):
                transport = Transport()
                fields = transport.services[0]["services"]["example_dot_phone_account"]["fields"]
                if change == "extra":
                    fields["new"] = copy.deepcopy(fields["server"])
                elif change == "missing":
                    del fields["server"]
                elif change == "optional":
                    fields["server"]["required"] = False
                else:
                    fields["server"]["selector"] = {"number": {}}
                with self.assertRaisesRegex(phone.PhoneError, "schema|required text"):
                    self.run_config(transport, apply=True)
                self.assertFalse(transport.posts)

    def test_unavailable_or_busy_roles_refuse_before_post(self):
        changes = [("sensor.example_dot_phone", value) for value in
                   ("unavailable", "unknown", "In call", "Ringing", "Calling", "Connecting")]
        changes += [("sensor.example_dot_phone_call", "peer"),
                    ("media_player.example_dot_speaker", "playing"),
                    ("assist_satellite.example_dot_assist_satellite", "responding")]
        for entity, value in changes:
            with self.subTest(entity=entity, value=value):
                transport = Transport([altered(states(), entity, value)])
                with self.assertRaises(phone.PhoneError):
                    self.run_config(transport, apply=True)
                self.assertFalse(transport.posts)

    def test_firmware_and_missing_native_role_fail_closed(self):
        invalid = states()
        invalid[0]["attributes"]["installed_version"] = "v1.0.39"
        for plan in (invalid, states()[1:], states() + [states()[0]]):
            transport = Transport([plan])
            with self.assertRaises(phone.PhoneError):
                self.run_config(transport, apply=True)
            self.assertFalse(transport.posts)

    def test_settings_drift_before_or_after_post_refuses_receipt(self):
        changed = altered(states("Ready"), "select.example_dot_wake_word", "different")
        for plan, post_count in (([states(), changed], 0), ([states(), states(), changed], 1)):
            with self.subTest(post_count=post_count):
                transport = Transport(plan)
                with self.assertRaisesRegex(phone.PhoneError, "settings changed"):
                    self.run_config(transport, apply=True)
                self.assertEqual(len(transport.posts), post_count)
                self.assertFalse(self.receipt.exists())

    def test_existing_plain_transport_is_preserved(self):
        plan = [altered(states(status), "switch.example_dot_phone_without_encryption", "on")
                for status in ("Not set up", "Not set up", "Ready")]
        transport = Transport(plan)
        self.run_config(transport, apply=True)
        self.assertEqual(len(transport.posts), 1)
        self.assertTrue(transport.posts[0][1].endswith("_phone_account"))

    def test_missing_receipt_directory_refuses_before_post(self):
        self.receipt = self.root / "missing" / "receipt.json"
        transport = Transport()
        with self.assertRaisesRegex(phone.PhoneError, "parent directory"):
            self.run_config(transport, apply=True)
        self.assertFalse(transport.posts)

    def cli_files(self):
        values = {"config": json.dumps(CONFIG), "ha-url-file": URL,
                  "token-file": "example.token.value"}
        argv = []
        for name, value in values.items():
            path = self.root / name
            path.write_text(value)
            path.chmod(0o600)
            argv.extend(["--" + name, str(path)])
        return argv + ["--receipt", str(self.receipt)]

    def test_cli_dry_run_has_no_secret_output_or_local_changes(self):
        argv = self.cli_files()
        before = {path: path.read_bytes() for path in self.root.iterdir()}
        output = io.StringIO()
        transport = Transport()
        with patch.object(phone, "HTTPTransport", return_value=transport), redirect_stdout(output):
            self.assertEqual(phone.main(argv), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "dry_run")
        for value in (CONFIG["password"], CONFIG["server"], URL, "example.token.value"):
            self.assertNotIn(value, output.getvalue())
        self.assertEqual({path: path.read_bytes() for path in self.root.iterdir()}, before)
        self.assertFalse(transport.posts)

    def test_credential_file_modes_refuse_before_network(self):
        for name in ("config", "ha-url-file", "token-file"):
            with self.subTest(name=name):
                argv = self.cli_files()
                (self.root / name).chmod(0o644)
                output = io.StringIO()
                with patch.object(phone, "HTTPTransport") as factory, redirect_stderr(output):
                    self.assertEqual(phone.main(argv), 1)
                factory.assert_not_called()
                self.assertIn("owner-only", output.getvalue())
                self.assertNotIn(str(self.root), output.getvalue())

    def test_private_input_symlink_directory_and_other_owner_rejected(self):
        path = self.root / "value"
        path.write_text("secret")
        path.chmod(0o600)
        link = self.root / "link"
        link.symlink_to(path)
        for bad in (link, self.root):
            with self.assertRaisesRegex(phone.PhoneError, "regular file"):
                phone.private_read(bad, "config")
        with patch.object(phone.os, "getuid", return_value=path.stat().st_uid + 1):
            with self.assertRaisesRegex(phone.PhoneError, "owner-only"):
                phone.private_read(path, "token")
        path.chmod(0o400)
        self.assertEqual(phone.private_read(path, "config"), "secret")

    def test_receipt_permissions_and_symlink_refuse_before_network(self):
        self.receipt.write_text("{}")
        self.receipt.chmod(0o644)
        transport = Transport()
        with self.assertRaisesRegex(phone.PhoneError, "owner-only"):
            self.run_config(transport, apply=True)
        self.assertFalse(transport.calls)
        self.receipt.unlink()
        self.receipt.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(phone.PhoneError, "symlink"):
            self.run_config(transport, apply=True)
        self.assertFalse(transport.calls)

    def test_receipt_cannot_replace_input_file(self):
        argv = self.cli_files()
        argv[-1] = str(self.root / "token-file")
        output = io.StringIO()
        with patch.object(phone, "HTTPTransport") as factory, redirect_stderr(output):
            self.assertEqual(phone.main(argv), 1)
        factory.assert_not_called()
        self.assertIn("must not overwrite", output.getvalue())

    def test_config_and_token_validation_redacts_values(self):
        for value in (dict(CONFIG, password=""), dict(CONFIG, password="example\nsecret"),
                      dict(CONFIG, server="sip:example-password@pbx.example.test"),
                      dict(CONFIG, extra="example-password")):
            with self.assertRaises(phone.PhoneError) as caught:
                phone.validate_config(value)
            self.assertNotIn("example-password", str(caught.exception))
        for value in ("", "token\nAuthorization: secret", "token with spaces"):
            with self.assertRaises(phone.PhoneError):
                phone.validate_token(value)

    def test_argparse_does_not_echo_accidental_secret(self):
        output = io.StringIO()
        with redirect_stderr(output), self.assertRaises(SystemExit):
            phone.main(["--password", "example-password"])
        self.assertNotIn("example-password", output.getvalue())


class HTTPTransportTests(unittest.TestCase):
    def test_https_and_plaintext_policy(self):
        self.assertEqual(phone.validate_url(URL), URL)
        self.assertEqual(phone.validate_url("http://127.0.0.1:8123/"), "http://127.0.0.1:8123")
        self.assertEqual(phone.validate_url("http://[::1]:8123"), "http://[::1]:8123")
        with self.assertRaisesRegex(phone.PhoneError, "allow-http-lan"):
            phone.validate_url("http://ha.example.test:8123")
        self.assertEqual(phone.validate_url("http://ha.example.test:8123", True), "http://ha.example.test:8123")
        for url in ("https://user:example-password@ha.example.test", URL + "/path",
                    URL + "?token=example-password", URL + "#fragment", "file:///etc/passwd"):
            with self.assertRaises(phone.PhoneError) as caught:
                phone.validate_url(url)
            self.assertNotIn("example-password", str(caught.exception))

    def test_tls_verification_and_environment_proxy_bypass(self):
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://proxy.example.test:8888"}):
            transport = phone.HTTPTransport(URL, "example.token.value")
        handlers = transport.opener.handlers
        https = next(h for h in handlers if isinstance(h, phone.urllib.request.HTTPSHandler))
        self.assertTrue(https._context.check_hostname)
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(any(isinstance(h, phone.urllib.request.ProxyHandler) and h.proxies for h in handlers))

    def test_redirects_never_forward_token_or_repeat_request(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            code = 302

            def do_GET(self):
                calls.append(self.path)
                self.send_response(self.code)
                self.send_header("Location", "/redirect-target")
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            transport = phone.HTTPTransport(f"http://127.0.0.1:{server.server_port}", "example.token.value")
            for code in (301, 302, 303, 307, 308):
                Handler.code = code
                calls.clear()
                with self.assertRaises(phone.PhoneError) as caught:
                    transport.request("GET", "/api/services")
                self.assertEqual(calls, ["/api/services"])
                self.assertNotIn("example.token.value", str(caught.exception))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
