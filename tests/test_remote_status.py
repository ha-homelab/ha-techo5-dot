import contextlib
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import remote_status as remote


EXAMPLE_KEY = "12" * 24


@contextlib.contextmanager
def server(status=200, body=None, content_type="application/json", location=None):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.command, self.path, dict(self.headers)))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            if location:
                self.send_header("Location", location)
            self.end_headers()
            payload = body if body is not None else json.dumps({"software": "v1.0.40"}).encode()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join(timeout=2)


class SigningTests(unittest.TestCase):
    def test_upstream_hmac_vector_includes_empty_body_digest_and_final_newline(self):
        result = remote.signature(EXAMPLE_KEY, "/api/v1/device", timestamp=1700000000,
                                  nonce="0123456789abcdef01234567")
        self.assertEqual(result, "v1 1700000000 0123456789abcdef01234567 "
                         "7d54a13ad9b9d4df20620a20c38ee2267a3f165e9c6e99774e9b874ce7d51e32")

    def test_signing_is_limited_to_fixed_get_paths(self):
        for path in ("/api/v1/entities/mic_mute", "/api/v1/logs", "/api/v1/device?x=1",
                     "/api/v1/device/../entities", "/setup"):
            with self.subTest(path=path), self.assertRaises(remote.RemoteStatusError):
                remote.signature(EXAMPLE_KEY, path)

    def test_each_request_has_new_nonce_and_path_is_authenticated(self):
        first = remote.signature(EXAMPLE_KEY, "/api/v1/device")
        second = remote.signature(EXAMPLE_KEY, "/api/v1/device")
        self.assertNotEqual(first.split()[2], second.split()[2])
        self.assertNotEqual(remote.signature(EXAMPLE_KEY, "/api/v1/device", timestamp=1, nonce="ab" * 12),
                            remote.signature(EXAMPLE_KEY, "/api/v1/entities", timestamp=1, nonce="ab" * 12))


class InputTests(unittest.TestCase):
    def test_valid_literal_origins(self):
        self.assertEqual(remote.validate_target("http://127.0.0.1/"), remote.Target("http", "127.0.0.1", 80))
        self.assertEqual(remote.validate_target("https://[::1]:1234"), remote.Target("https", "::1", 1234))

    def test_rejects_ambiguous_targets_before_connecting(self):
        bad = ["http://localhost", "http://127.1", "http://2130706433", "http://127.0.0.1:080",
               "http://127.0.0.1:", "http://127.0.0.1:0", "http://127.0.0.1:65536",
               "http://user:password@127.0.0.1", "http://127.0.0.1/path",
               "http://127.0.0.1?", "http://127.0.0.1#", "ftp://127.0.0.1",
               "http://[::1%25eth0]", "http://0.0.0.0", "http://[ff02::1]",
               "http://127.0.0.1\n", "http://127.0.0.1\\@other.example"]
        for origin in bad:
            with self.subTest(origin=origin), self.assertRaises(remote.RemoteStatusError):
                remote.validate_target(origin)

    def test_private_key_file_checks_opened_inode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "api-key.txt"
            path.write_text(EXAMPLE_KEY + "\n")
            path.chmod(0o600)
            self.assertEqual(remote.load_key(path), EXAMPLE_KEY)
            path.chmod(0o644)
            with self.assertRaises(remote.RemoteStatusError):
                remote.load_key(path)
            path.chmod(0o600)
            link = path.with_name("link")
            link.symlink_to(path)
            with self.assertRaises(remote.RemoteStatusError):
                remote.load_key(link)
            with self.assertRaises(remote.RemoteStatusError):
                remote.load_key(Path(directory))
            path.write_bytes(b"x" * 129)
            with self.assertRaises(remote.RemoteStatusError):
                remote.load_key(path)

    def test_environment_key_and_missing_invalid_values(self):
        with patch.dict(os.environ, {remote.KEY_ENV: EXAMPLE_KEY}):
            self.assertEqual(remote.load_key(None), EXAMPLE_KEY)
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(remote.RemoteStatusError):
            remote.load_key(None)
        for value in ("", "abcd", "g" * 48, EXAMPLE_KEY + "\nextra"):
            with patch.dict(os.environ, {remote.KEY_ENV: value}), self.assertRaises(remote.RemoteStatusError):
                remote.load_key(None)

    def test_cli_never_echoes_an_accidentally_pasted_key(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            self.assertEqual(remote.main(["http://127.0.0.1", "--key", EXAMPLE_KEY]), 1)
        self.assertNotIn(EXAMPLE_KEY, output.getvalue())


class TransportTests(unittest.TestCase):
    def test_real_get_is_signed_correctly_without_using_proxy_environment(self):
        with server() as (origin, requests), patch.dict(os.environ, {
                "http_proxy": "http://127.0.0.1:1", "HTTP_PROXY": "http://127.0.0.1:1"}):
            self.assertEqual(remote.fetch_status(origin, "device", EXAMPLE_KEY), {"software": "v1.0.40"})
        self.assertEqual(len(requests), 1)
        method, path, headers = requests[0]
        self.assertEqual((method, path), ("GET", "/api/v1/device"))
        version, timestamp, nonce, digest = headers["X-Techo5-Remote"].split()
        self.assertEqual(version, "v1")
        self.assertEqual(len(nonce), 24)
        derived = hmac.digest(b"techo5-remote v1", EXAMPLE_KEY.encode(), "sha256")
        message = f"v1\nGET\n/api/v1/device\n{timestamp}\n{nonce}\n{hashlib.sha256(b'').hexdigest()}\n"
        self.assertEqual(digest, hmac.new(derived, message.encode(), hashlib.sha256).hexdigest())
        self.assertNotIn(EXAMPLE_KEY, json.dumps(headers))

    def test_entities_read_and_response_shape(self):
        with server(body=b'[{"id":"volume","kind":"number","state":50}]') as (origin, requests):
            self.assertEqual(remote.fetch_status(origin, "entities", EXAMPLE_KEY)[0]["id"], "volume")
        self.assertEqual(requests[0][1], "/api/v1/entities")
        with server(body=b"{}") as (origin, _), self.assertRaises(remote.RemoteStatusError):
            remote.fetch_status(origin, "entities", EXAMPLE_KEY)

    def test_redirect_is_never_followed_and_request_not_retried(self):
        with server() as (destination, destination_requests):
            with server(status=302, location=destination + "/api/v1/device") as (origin, requests):
                with self.assertRaisesRegex(remote.RemoteStatusError, "not followed"):
                    remote.fetch_status(origin, "device", EXAMPLE_KEY)
        self.assertEqual(len(requests), 1)
        self.assertEqual(destination_requests, [])

    def test_http_errors_do_not_surface_response_body(self):
        for status in (401, 429, 500):
            with self.subTest(status=status), server(status=status, body=EXAMPLE_KEY.encode()) as (origin, requests):
                with self.assertRaises(remote.RemoteStatusError) as caught:
                    remote.fetch_status(origin, "device", EXAMPLE_KEY)
                self.assertNotIn(EXAMPLE_KEY, str(caught.exception))
                self.assertEqual(len(requests), 1)

    def test_rejects_non_json_malformed_and_oversized_responses(self):
        for body, content_type in ((b"{}", "text/html"), (b"not-json", "application/json"),
                                   (b'"' + b"x" * 128 + b'"', "application/json")):
            with self.subTest(content_type=content_type), patch.object(remote, "MAX_RESPONSE_BYTES", 128):
                with server(body=body, content_type=content_type) as (origin, _):
                    with self.assertRaises(remote.RemoteStatusError):
                        remote.fetch_status(origin, "device", EXAMPLE_KEY)

    def test_unsupported_resource_and_timeout_do_not_connect(self):
        with patch.object(remote.http.client, "HTTPConnection") as connection:
            for resource, timeout in (("logs", 10), ("device", float("nan")), ("device", 0), ("device", 31)):
                with self.assertRaises(remote.RemoteStatusError):
                    remote.fetch_status("http://127.0.0.1", resource, EXAMPLE_KEY, timeout=timeout)
            connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
