"""Exercise the readiness predicate against actual HA update-state semantics.

The predicate deliberately uses the common Python/Jinja expression subset, so
these state combinations need no Home Assistant instance or optional packages.
"""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "examples/home-assistant/techo5-capabilities-package.yaml"


class ReadinessScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = json.loads(PACKAGE.read_text())
        sensor = next(
            sensor
            for section in package["template"]
            for sensor in section.get("binary_sensor", [])
            if sensor["unique_id"] == "techo5_example_ready"
        )
        cls.predicate = sensor["state"].strip()[2:-2].strip()

    def ready(self, update_state="off", in_progress=False, overrides=None):
        states = {
            "assist_satellite.echo_dot_example_assist_satellite": "idle",
            "media_player.echo_dot_example_speaker": "idle",
            "sensor.echo_dot_example_now_playing_state": "idle",
            "binary_sensor.echo_dot_example_sounding": "off",
            "binary_sensor.echo_dot_example_alarm_sounding": "off",
            "binary_sensor.echo_dot_example_timer_sounding": "off",
            "switch.echo_dot_example_microphone_microphone_mute": "off",
            "sensor.echo_dot_example_phone_call": "",
            "update.echo_dot_example_firmware": update_state,
            "light.echo_dot_example_ring_led_ring": "off",
        }
        states.update(overrides or {})

        def state_attr(entity_id, attribute):
            if entity_id == "update.echo_dot_example_firmware" and attribute == "in_progress":
                return in_progress
            return None

        return bool(eval(self.predicate, {"__builtins__": {}}, {
            "states": lambda entity_id: states.get(entity_id, "unknown"),
            "is_state": lambda entity_id, expected: states.get(entity_id) == expected,
            "state_attr": state_attr,
            "true": True,
            "false": False,
            "none": None,
        }))

    def test_idle_device_is_ready_even_when_an_update_is_only_available(self):
        for state in ["off", "on"]:
            with self.subTest(update_state=state):
                self.assertTrue(self.ready(update_state=state, in_progress=False))

    def test_installation_and_missing_firmware_state_are_not_ready(self):
        for state in ["off", "on"]:
            with self.subTest(update_state=state):
                self.assertFalse(self.ready(update_state=state, in_progress=True))
        for state in ["unknown", "unavailable"]:
            with self.subTest(update_state=state):
                self.assertFalse(self.ready(update_state=state))

    def test_native_priority_states_prevent_custom_effects(self):
        for entity_id, value in {
            "assist_satellite.echo_dot_example_assist_satellite": "listening",
            "media_player.echo_dot_example_speaker": "playing",
            "sensor.echo_dot_example_now_playing_state": "playing",
            "binary_sensor.echo_dot_example_sounding": "on",
            "binary_sensor.echo_dot_example_alarm_sounding": "on",
            "binary_sensor.echo_dot_example_timer_sounding": "on",
            "switch.echo_dot_example_microphone_microphone_mute": "on",
            "sensor.echo_dot_example_phone_call": "Connected",
            "light.echo_dot_example_ring_led_ring": "unavailable",
        }.items():
            with self.subTest(entity_id=entity_id):
                self.assertFalse(self.ready(overrides={entity_id: value}))


if __name__ == "__main__":
    unittest.main()
