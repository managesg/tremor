"""Public negative control for adding a second monitor at a matched threshold."""

import json

from lab.l8_activation_control import _episodes, calibrate, evaluate


def compare():
    clean = ((10, 100, 0), (10, 0, 100), (10, 80, 80), (370, 0, 0))
    failures = ((60, 100, 100), (70, 70, 0), (30, 0, 100), (40, 0, 0))
    calibration = calibrate(_episodes("l8-negative-fit", clean))
    heldout = _episodes("l8-negative-clean", clean)
    heldout.extend(_episodes("l8-negative-failure", failures, failure=True))
    return {
        "scientific_result": False,
        "control": "weak_text_only_signals",
        "assessment": evaluate(calibration, heldout),
    }


if __name__ == "__main__":
    print(json.dumps(compare(), default=str, indent=2, sort_keys=True, allow_nan=False))
