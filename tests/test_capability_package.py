"""Validate the public HA package without installing HA or third-party parsers.

The examples intentionally use JSON-compatible YAML, so the same source is
checked by CI and loaded by Home Assistant. These are deployment-contract
checks, not a replacement for HA's config check or the room acceptance test.
"""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "examples/home-assistant/techo5-capabilities-package.yaml"
CARD = ROOT / "examples/home-assistant/capabilities-card.yaml"


def dictionaries(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)


class CapabilityPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads(PACKAGE.read_text())
        cls.card = json.loads(CARD.read_text())
        cls.catalog = json.loads(
            (ROOT / "docs/reference/actions-v1.0.40.json").read_text()
        )["services"]

    def test_native_services_and_all_required_arguments_match_live_catalog(self):
        calls = 0
        for node in dictionaries(self.package):
            action = node.get("action", "")
            if not action.startswith("esphome."):
                continue
            calls += 1
            with self.subTest(action=action):
                schema = self.catalog[action.removeprefix("esphome.")]
                self.assertEqual(set(node.get("data", {})), set(schema["fields"]))
                if "response_variable" in node:
                    self.assertIn("response", schema)
        self.assertGreater(calls, 10)

    def test_every_script_requires_explicit_enable_and_available_device(self):
        for name, script in self.package["script"].items():
            with self.subTest(script=name):
                sequence = script["sequence"]
                self.assertEqual(sequence[0], {
                    "condition": "state",
                    "entity_id": "input_boolean.techo5_example_enabled",
                    "state": "on",
                })
                self.assertEqual(sequence[1]["condition"], "state")
                self.assertIn(sequence[1]["entity_id"], {
                    "binary_sensor.techo5_example_ready",
                    "binary_sensor.techo5_example_connected",
                })
                self.assertEqual(sequence[1]["state"], "on")
                self.assertEqual(script["mode"], "single")

    def test_opt_ins_are_never_forced_on_by_loading_package(self):
        for config in self.package["input_boolean"].values():
            self.assertFalse(config.get("initial", False))
        for node in dictionaries(self.package):
            self.assertNotEqual(node.get("action"), "input_boolean.turn_on")

    def test_radio_modes_require_conflicting_receiver_off_before_enable(self):
        sequence = self.package["script"]["techo5_example_media_profile"]["sequence"]
        switch = next(step for step in sequence if "choose" in step)
        for path, disabled, enabled in [
            (switch["choose"][0]["sequence"], "bluetooth_phone", "bluetooth_proxy"),
            (switch["default"], "bluetooth_proxy", "bluetooth_phone"),
        ]:
            with self.subTest(enabled=enabled):
                self.assertEqual(path[0]["action"], "switch.turn_off")
                self.assertEqual(path[0]["target"]["entity_id"], f"switch.echo_dot_example_{disabled}")
                self.assertIn(f"is_state('switch.echo_dot_example_{disabled}', 'off')", path[1]["wait_template"])
                self.assertFalse(path[1]["continue_on_timeout"])
                self.assertEqual(path[1]["timeout"], "00:00:10")
                self.assertEqual(path[2]["entity_id"], "binary_sensor.techo5_example_ready")
                self.assertEqual(path[3]["action"], "switch.turn_on")
                self.assertIn(f"switch.echo_dot_example_{enabled}", path[3]["target"]["entity_id"])

    def test_ring_restoration_requires_unchanged_state_and_native_idle(self):
        sequence = self.package["script"]["techo5_example_ring_scene"]["sequence"]
        snapshot = next(i for i, step in enumerate(sequence) if step.get("action") == "scene.create")
        painting = next(i for i, step in enumerate(sequence) if step.get("action") == "light.turn_on")
        self.assertLess(snapshot, painting)
        restoration = next(step for step in sequence if "if" in step)
        guard = restoration["if"][0]["value_template"]
        self.assertIn("wait.completed", guard)
        self.assertIn("last_updated) == owned_update", guard)
        self.assertEqual(restoration["then"][0]["action"], "scene.turn_on")
        self.assertEqual(sequence[-1]["action"], "scene.delete")
        # No unbounded wait/delay, or restore outside the ownership condition.
        for step in sequence:
            if "wait_template" in step:
                self.assertIn("timeout", step)
            self.assertNotEqual(step.get("action"), "scene.turn_on")

    def test_timers_and_alarms_never_cancel_everything(self):
        for node in dictionaries(self.package):
            action = node.get("action", "")
            if action.startswith("esphome.") and "id" in node.get("data", {}):
                self.assertNotEqual(node["data"]["id"], "all")
                self.assertEqual(node["data"]["id"], "{{ owned_id }}")
        for name in ("timer_control", "alarm_control"):
            seq = self.package["script"][f"techo5_example_{name}"]["sequence"]
            listing = next(i for i, n in enumerate(seq) if n.get("action", "").endswith("_alarms_list"))
            mutations = next(i for i, n in enumerate(seq) if "choose" in n)
            self.assertLess(listing, mutations)
            self.assertTrue(any("ours|length == 1" in n.get("value_template", "") for n in seq[listing:mutations]))
            self.assertIn("^techo5_example: ", json.dumps(seq[listing:mutations]))

    def test_household_mutations_are_fixed_lights_and_clap_is_device_bound(self):
        allowed = {"light.echo_dot_example_ring_led_ring", "light.example_kitchen_strip", "light.example_kitchen_table"}
        for node in dictionaries(self.package):
            if node.get("action") not in {"light.turn_on", "light.turn_off"}:
                continue
            targets = node["target"]["entity_id"]
            targets = [targets] if isinstance(targets, str) else targets
            self.assertLessEqual(set(targets), allowed)
        clap = next(a for a in self.package["automation"] if a["id"].endswith("double_clap"))
        self.assertEqual(clap["triggers"][0]["event_data"], {"gesture": "double_clap", "device": "Echo Dot Example"})
        self.assertIn({"condition": "state", "entity_id": "input_boolean.techo5_example_clap_light", "state": "on"}, clap["conditions"])
        seq = self.package["script"]["techo5_example_toggle_lights"]["sequence"]
        self.assertEqual(seq[-1], {"delay": "00:00:03"})

    def test_reminder_is_local_and_has_separate_verified_ownership(self):
        scripts = self.package["script"]
        create = scripts["techo5_example_reminder_set"]["sequence"]
        call = next(step for step in create if step.get("action", "").endswith("_reminder_set"))
        self.assertEqual(call["data"]["ring_on"], "")
        self.assertEqual(call["response_variable"], "created")
        saved = {step.get("target", {}).get("entity_id") for step in create
                 if step.get("action") == "input_text.set_value"}
        self.assertEqual(saved, {
            "input_text.techo5_example_reminder_id",
            "input_text.techo5_example_reminder_owned_label",
        })
        self.assertNotIn("input_text.techo5_example_alarm_id", saved)
        self.assertIn("created.id", json.dumps(create))
        control = scripts["techo5_example_reminder_control"]["sequence"]
        before_mutation = control[:next(i for i, step in enumerate(control) if "choose" in step)]
        text = json.dumps(before_mutation)
        self.assertIn("selectattr('reminder','equalto',true)", text)
        self.assertIn("selectattr('id','equalto',owned_id)", text)
        self.assertIn("selectattr('label','equalto',owned_words)", text)
        self.assertIn("ours|length == 1", text)
        for step in dictionaries(control):
            if step.get("action", "").startswith("esphome.") and "id" in step.get("data", {}):
                self.assertEqual(step["data"]["id"], "{{ owned_id }}")

    def test_spoken_reminder_mode_does_not_fall_through_to_alarm_creation(self):
        self.assertIn("Spoken reminder", self.package["input_select"]["techo5_example_alarm_mode"]["options"])
        sequence = self.package["script"]["techo5_example_alarm_set"]["sequence"]
        branch = next(step for step in sequence if "if" in step)
        self.assertIn("style == 'Spoken reminder'", branch["if"][0]["value_template"])
        self.assertEqual(branch["then"][0]["action"], "script.techo5_example_reminder_set")
        self.assertIn("stop", branch["then"][-1])
        self.assertLess(sequence.index(branch), next(i for i, step in enumerate(sequence) if "choose" in step))

    def test_history_cards_use_verified_existing_maintenance_entities(self):
        maintenance = (ROOT / "examples/home-assistant/maintenance-card.yaml").read_text()
        graphs = [c for c in self.card["cards"] if c.get("type") == "history-graph"]
        self.assertEqual(len(graphs), 2)
        for graph in graphs:
            self.assertEqual(graph["hours_to_show"], 6)
            for entity in graph["entities"]:
                self.assertIn("entity: " + entity + "\n", maintenance)

    def test_peer_call_is_explicit_fixed_and_requires_registered_phone(self):
        call = self.package["script"]["techo5_example_call_peer"]
        self.assertNotIn("fields", call)
        self.assertIn({"condition": "state", "entity_id": "sensor.echo_dot_example_phone", "state": "Ready"}, call["sequence"])
        self.assertEqual(call["sequence"][-1], {
            "action": "esphome.echo_dot_example_phone_call_named",
            "data": {"number": "201", "name": "Other Dot"},
        })
        buttons = [n for n in dictionaries(self.card) if n.get("perform_action") == "script.techo5_example_call_peer"]
        self.assertEqual(len(buttons), 1)
        self.assertIn("confirmation", buttons[0])
        self.assertNotIn("script.techo5_example_call_peer", json.dumps(self.package["automation"]))

    def test_no_reboots_recording_microphone_or_credential_writes(self):
        forbidden = ("restart", "reboot", "announce_house", "ssh_keys", "wifi", "phone_account", "microphone_gain", "microphone_mixing", "wake_word", "keep_wake_clips", "stream_microphone")
        for node in dictionaries(self.package):
            action = node.get("action", "")
            if not action:
                continue
            invocation = json.dumps({"action": action, "target": node.get("target")})
            self.assertFalse(any(term in invocation for term in forbidden), invocation)
        health = next(a for a in self.package["automation"] if a["id"].endswith("availability_notice"))
        self.assertTrue(all(t["for"] == "00:05:00" for t in health["triggers"]))
        self.assertEqual(health["actions"][0]["action"], "persistent_notification.create")

    def test_dashboard_scripts_exist_and_required_fields_are_supplied(self):
        for node in dictionaries(self.card):
            action = node.get("perform_action", "")
            if not action.startswith("script."):
                continue
            config = self.package["script"][action.removeprefix("script.")]
            required = {key for key, field in config.get("fields", {}).items() if field.get("required")}
            self.assertLessEqual(required, set(node.get("data", {})))


if __name__ == "__main__":
    unittest.main()
