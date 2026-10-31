"""Offline rollback regression tests. Never connects to a real device."""
import hashlib
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("deploy_daemon", HERE / "deploy_daemon.py")
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class Rollback(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.job = self.root / "job"
        self.job.mkdir()
        self.target = self.root / "echod"
        self.target.write_bytes(b"new-binary")
        self.old = hashlib.sha256(b"old-binary").hexdigest()
        self.new = hashlib.sha256(b"new-binary").hexdigest()
        (self.job / "echod.previous").write_bytes(b"old-binary")
        (self.job / "params").write_text(f"OLD={self.old}\nNEW={self.new}\nID=test\n")
        self.hold = self.root / "hold"
        self.lock = self.root / "lock"
        self.lock.mkdir()
        (self.lock / "owner").write_text(str(self.job) + "\n")
        self.proc = self.root / "proc"
        self.proc.mkdir()
        busybox = self.root / "busybox"
        busybox.write_text('''#!/usr/bin/env python3
import hashlib, os, pathlib, sys
command, *args = sys.argv[1:]
root = pathlib.Path(__file__).parent
if command == "sleep": sys.exit(0)
if command == "pidof":
    if (root / "proc/123/exe").exists(): print("123")
    sys.exit(0)
if command == "sha256sum":
    print(hashlib.sha256(pathlib.Path(args[0]).read_bytes()).hexdigest(), args[0])
    sys.exit(0)
if command == "kill": raise RuntimeError("Rollback MUST NOT kill a process")
os.execvp(command, [command, *args])
''')
        busybox.chmod(0o755)
        code = (HERE / "maintenance.sh").read_text()
        for old, new in (("BB=/bin/busybox.static", "BB=" + str(busybox)),
                         ("TARGET=/usr/local/bin/echod", "TARGET=" + str(self.target)),
                         ("HOLD=/run/techo5/hold", "HOLD=" + str(self.hold)),
                         ("LOCK=/run/techo5/myshka-maintenance", "LOCK=" + str(self.lock)),
                         ("/proc/", str(self.proc) + "/")):
            code = code.replace(old, new)
        self.script = self.job / "maintenance.sh"
        self.script.write_text(code)

    def run_watch(self):
        return subprocess.run(["sh", str(self.script), str(self.job), "watch"],
                              capture_output=True, text=True, timeout=10)

    def test_running_process_is_not_killed(self):
        (self.proc / "123").mkdir()
        (self.proc / "123/exe").write_bytes(b"new-binary")
        self.hold.write_text(str(self.job) + "\n")
        result = self.run_watch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.target.read_bytes(), b"old-binary")
        self.assertEqual((self.proc / "123/exe").read_bytes(), b"new-binary")
        self.assertEqual((self.job / "state").read_text().strip(), "rollback_staged_restart_required")
        self.assertFalse(self.hold.exists())

    def test_foreign_hold_is_preserved(self):
        self.hold.write_text("someone-else\n")
        self.assertEqual(self.run_watch().returncode, 0)
        self.assertEqual(self.hold.read_text(), "someone-else\n")
        self.assertEqual(self.target.read_bytes(), b"old-binary")

    def test_unexpected_binary_not_overwritten(self):
        self.target.write_bytes(b"third-party-update")
        self.assertNotEqual(self.run_watch().returncode, 0)
        self.assertEqual(self.target.read_bytes(), b"third-party-update")

    def test_ack_preserves_new_binary(self):
        (self.job / "ack").write_text(self.new + "\n")
        self.assertEqual(self.run_watch().returncode, 0)
        self.assertEqual(self.target.read_bytes(), b"new-binary")
        self.assertEqual((self.job / "state").read_text().strip(), "confirmed")

    def test_bad_backup_is_rejected(self):
        (self.job / "echod.previous").write_bytes(b"damaged")
        self.assertNotEqual(self.run_watch().returncode, 0)
        self.assertEqual(self.target.read_bytes(), b"new-binary")


class IdleGuards(unittest.TestCase):
    def test_cannot_override_core_guard(self):
        args = SimpleNamespace(prefix="example", idle_entity=["sensor.example_phone=Busy"])
        with self.assertRaises(ValueError):
            deploy.expected_states(args)

    def test_missing_entity_fails_closed(self):
        ha = deploy.HA("http://127.0.0.1:8123", "unused-test-token")
        ha.request = lambda _: []
        with self.assertRaises(ValueError):
            ha.stable_idle({"sensor.required": "idle"})


class MaintenanceRouting(unittest.TestCase):
    def arguments(self, service_prefix=None):
        args = ["deploy_daemon.py", "ack", "--host", "192.0.2.1", "--identity", "/unused/key",
                "--known-hosts", "/unused/hosts", "--old-sha256", "a" * 64,
                "--new-sha256", "b" * 64, "--job", "c" * 32,
                "--ha-url", "http://127.0.0.1:8123", "--ha-token-file", "/unused/token",
                "--prefix", "original_dot"]
        for name in ("general", "alarm", "timer"):
            args.extend(["--idle-entity", f"binary_sensor.original_dot_{name}=off"])
        if service_prefix is not None:
            args.extend(["--service-prefix", service_prefix])
        return args

    def test_renamed_action_keeps_original_entity_guards(self):
        for supplied, expected in ((None, "original_dot"), ("renamed_dot", "renamed_dot")):
            with self.subTest(service_prefix=supplied):
                ha = Mock()
                ha.request.side_effect = lambda path, data: {"service_response": {
                    "request_id": data["request_id"], "boot_id": "test-boot",
                    "protocol": "cisco-announcement-v1", **dict.fromkeys(deploy.FLAGS, True)}}
                with patch.object(deploy.sys, "argv", self.arguments(supplied)), \
                     patch.object(deploy, "HA", return_value=ha), \
                     patch.object(deploy, "read_token", return_value="unused-test-token"), \
                     patch.object(deploy, "invoke") as invoke, redirect_stdout(io.StringIO()):
                    deploy.main()
                self.assertEqual(ha.request.call_count, 1)
                self.assertEqual(ha.request.call_args.args[0],
                                 f"/api/services/esphome/{expected}_guarded_announcement_capabilities?return_response")
                self.assertEqual(ha.stable_idle.call_count, 2)
                for call in ha.stable_idle.call_args_list:
                    guards = call.args[0]
                    self.assertEqual(guards["assist_satellite.original_dot_assist_satellite"], "idle")
                    self.assertEqual(guards["sensor.original_dot_phone"], "Ready")
                    self.assertTrue(all(".original_dot_" in entity for entity in guards))
                self.assertEqual(invoke.call_args.args[2], "ack")

    def test_invalid_service_prefix_is_refused_before_transport(self):
        for supplied in ("", "renamed-dot", "../other", "dot?extra=1", "two dots"):
            with self.subTest(service_prefix=supplied), \
                 patch.object(deploy.sys, "argv", self.arguments(supplied)), \
                 patch.object(deploy, "HA") as ha, patch.object(deploy, "read_token") as token:
                with self.assertRaises(ValueError):
                    deploy.main()
                ha.assert_not_called()
                token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
