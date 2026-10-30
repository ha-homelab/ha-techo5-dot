"""Regression cases for the actual ring-feedback templates, without a live HA.

TECHO5 has reported brightness-scaled RGB values. These cases render the
package's own expressions instead of reimplementing its color comparison.
The tiny evaluator supports only the expression/filter subset used here.
"""

import io
import json
from pathlib import Path
import re
from types import SimpleNamespace
import tokenize
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _tokens(expression):
    ignored = {tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL}
    return [token.string for token in tokenize.generate_tokens(io.StringIO(expression).readline)
            if token.type not in ignored]


def _atom_start(tokens, end):
    """Locate the primary expression immediately before a postfix filter."""
    if tokens[end] not in (")", "]"):
        return end
    closer = tokens[end]
    opener = "(" if closer == ")" else "["
    depth = 1
    start = end
    while depth:
        start -= 1
        depth += (tokens[start] == closer) - (tokens[start] == opener)
    # Include the callable/subscripted name, but not an infix keyword.
    if start and (tokens[start - 1] in (")", "]") or
                  re.fullmatch(r"[A-Za-z_]\w*", tokens[start - 1]) and
                  tokens[start - 1] not in {"and", "or", "not", "if", "else"}):
        return _atom_start(tokens, start - 1)
    return start


def _filtered_expression(expression):
    """Translate generic postfix Jinja filters to function calls."""
    tokens = _tokens(expression)
    while "|" in tokens:
        pipe = tokens.index("|")
        start = _atom_start(tokens, pipe - 1)
        name = tokens[pipe + 1]
        end = pipe + 2
        arguments = []
        if end < len(tokens) and tokens[end] == "(":
            depth = 1
            cursor = end + 1
            while depth:
                depth += (tokens[cursor] == "(") - (tokens[cursor] == ")")
                cursor += 1
            arguments = tokens[end + 1:cursor - 1]
            end = cursor
        replacement = ["_filters", "[", repr(name), "]", "("] + tokens[start:pipe]
        if arguments:
            replacement += [","] + arguments
        replacement += [")"]
        tokens[start:end] = replacement
    return " ".join(tokens)


def _number(converter):
    def convert(value, default=0):
        try:
            return converter(value)
        except (TypeError, ValueError):
            return default
    return convert


def render(template, context):
    values = dict(context)
    values.update({"true": True, "false": False, "none": None})
    values["_filters"] = {
        "abs": abs, "max": max, "length": len,
        "float": _number(float), "int": _number(int),
    }
    for statement in re.findall(r"{%\s*set\s+(.*?)\s*%}", template):
        name, expression = statement.split("=", 1)
        values[name.strip()] = eval(_filtered_expression(expression.strip()),
                                    {"__builtins__": {}}, values)
    expression = re.search(r"{{\s*(.*?)\s*}}", template, re.DOTALL).group(1)
    return bool(eval(_filtered_expression(expression), {"__builtins__": {}}, values))


class RingFeedback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = json.loads((ROOT / "examples/home-assistant/techo5-capabilities-package.yaml").read_text())
        sequence = package["script"]["techo5_example_ring_scene"]["sequence"]
        cls.feedback = next(step["wait_template"] for step in sequence if "wait_template" in step)
        cls.restore = next(step["if"][0]["value_template"] for step in sequence if "if" in step)

    def context(self, raw, brightness=90, target=None, reported_at=2, on=True):
        ring = "light.echo_dot_example_ring_led_ring"
        attributes = {"rgb_color": raw, "brightness": brightness}
        return {
            "rgb": target or [30, 200, 80], "level": brightness,
            "previous_update": 1, "owned_update": 2,
            "states": {ring: SimpleNamespace(last_updated=reported_at)},
            "state_attr": lambda entity, key: attributes.get(key),
            "as_timestamp": lambda value: value,
            "is_state": lambda entity, state: on and state == "on",
            "wait": SimpleNamespace(completed=True),
        }

    def test_observed_scaled_rgb_and_unscaled_feedback_are_accepted(self):
        cases = [
            # Actual live report after requesting RGB [30, 200, 80] at 90.
            ([14, 90, 36], 90, [30, 200, 80]),
            ([30, 200, 80], 90, [30, 200, 80]),
            # Dim amber night-light feedback includes integer quantization.
            ([25, 12, 2], 25, [255, 120, 20]),
        ]
        for raw, brightness, target in cases:
            with self.subTest(raw=raw):
                self.assertTrue(render(self.feedback, self.context(raw, brightness, target)))

    def test_a_different_hue_does_not_acquire_ownership(self):
        self.assertFalse(render(self.feedback, self.context([90, 14, 36])))

    def test_missing_black_or_incomplete_feedback_is_rejected_without_division_errors(self):
        for raw in (None, [], [14, 90], [0, 0, 0]):
            with self.subTest(raw=raw):
                self.assertFalse(render(self.feedback, self.context(raw)))
        self.assertFalse(render(self.feedback, self.context([14, 90, 36], target=[0, 0, 0])))

    def test_freshness_power_and_brightness_still_gate_ownership(self):
        self.assertFalse(render(self.feedback, self.context([14, 90, 36], reported_at=1)))
        self.assertFalse(render(self.feedback, self.context([14, 90, 36], on=False)))
        context = self.context([14, 90, 36], brightness=70)
        context["level"] = 90
        self.assertFalse(render(self.feedback, context))

    def test_later_state_change_or_lost_idle_prevents_restoration(self):
        self.assertTrue(render(self.restore, self.context([14, 90, 36])))
        self.assertFalse(render(self.restore, self.context([14, 90, 36], reported_at=3)))
        context = self.context([14, 90, 36])
        context["wait"] = SimpleNamespace(completed=False)
        self.assertFalse(render(self.restore, context))


if __name__ == "__main__":
    unittest.main()
