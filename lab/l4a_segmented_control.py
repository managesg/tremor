"""Scripted measured-compression fit, then separately pinned held-out scoring."""

from fractions import Fraction
import json
from unicodedata import normalize

from lab.l4_measured_compression import audit, pin
from lab.l4a_exact_fit import fit as fit_models, predict


KNOTS = (Fraction(3, 10), Fraction(2, 5), Fraction(1, 2))


def _rational(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def _id(value):
    return type(value) is str and bool(value) and value == value.strip() and value == normalize("NFC", value)


def _observations(chains, expected_pin):
    if type(chains) is not list or not chains or pin(chains) != expected_pin:
        raise ValueError("chain inventory differs from its expected pin")
    chain_points, families, snapshot_pins, episodes = {}, set(), set(), set()
    loaded_notes, raw_sources = set(), set()
    settings = None
    for chain in chains:
        if (type(chain) is not dict or chain.keys() != {"id", "family", "levels"} or not _id(chain["id"])
                or not _id(chain["family"]) or chain["id"] in chain_points or chain["family"] in families
                or type(chain["levels"]) is not list):
            raise ValueError("invalid or repeated chain/family")
        by_setting = {}
        for level in chain["levels"]:
            if (type(level) is not dict or level.keys() != {"setting", "snapshot", "snapshot_pin", "false_notes"}
                    or not _id(level["setting"]) or level["setting"] in by_setting):
                raise ValueError("invalid or repeated level")
            snapshot, snapshot_pin = level["snapshot"], level["snapshot_pin"]
            payload = audit(snapshot, expected_pin=snapshot_pin)["loaded_bytes"]
            if snapshot["cutoff"] != 6 or not payload["before"] or not snapshot["loaded_after"]:
                raise ValueError("measured level requires complete six-night payload and false-share inventories")
            size = len(snapshot["loaded_after"])
            false = level["false_notes"]
            if type(false) is not int or not 0 <= false <= size or snapshot_pin in snapshot_pins:
                raise ValueError("invalid false count or repeated snapshot")
            snapshot_pins.add(snapshot_pin)
            episodes.update(row["id"] for row in snapshot["raw_before"])
            raw_sources.update(row["source"] for row in snapshot["raw_before"])
            loaded_notes.update(row["id"] for field in ("loaded_before", "loaded_after") for row in snapshot[field])
            by_setting[level["setting"]] = (Fraction(payload["after"], payload["before"]), Fraction(false, size))
        levels = sorted(by_setting)
        if len(levels) < 7 or len({point[0] for point in by_setting.values()}) != len(levels):
            raise ValueError("at least seven distinct measured levels are required per chain")
        if settings is not None and settings != levels:
            raise ValueError("chains differ in level inventory")
        settings = levels
        chain_points[chain["id"]] = list(by_setting.values())
        families.add(chain["family"])
    return chain_points, {"chain_ids": sorted(chain_points), "families": sorted(families), "settings": settings,
                          "snapshot_pins": sorted(snapshot_pins), "raw_episodes": sorted(episodes),
                          "loaded_notes": sorted(loaded_notes), "raw_sources": sorted(raw_sources)}


def _serialize(model):
    result = {"coefficients": [_rational(value) for value in model["coefficients"]], "rss": _rational(model["rss"])}
    if "knot" in model:
        result["knot"] = _rational(model["knot"])
    return result


def fit_training(chains, *, expected_training_pin, knots):
    observations, scope = _observations(chains, expected_training_pin)
    # Every eligible chain has the same measured level inventory and row count.
    fitted = fit_models([point for chain in observations.values() for point in chain], knots=knots)
    hinge = fitted["hinge"]["coefficients"]
    return {"scope": "scripted_l4a_fit", "training_sha256": expected_training_pin, "training": scope,
            "line": _serialize(fitted["line"]), "hinge": _serialize(fitted["hinge"]),
            "slopes": {"left": _rational(hinge[1]), "right": _rational(hinge[1] + hinge[2])},
            "candidate_rss": [{"knot": _rational(knot), "rss": _rational(rss)} for knot, rss in fitted["candidate_rss"]],
            "tied_knots": [_rational(knot) for knot in fitted["tied_knots"]]}


def _decode_model(model):
    result = {"coefficients": tuple(Fraction(**value) for value in model["coefficients"])}
    if "knot" in model:
        result["knot"] = Fraction(**model["knot"])
    return result


def score_holdout(chains, fitted, *, expected_holdout_pin, expected_fit_pin):
    if type(fitted) is not dict or pin(fitted) != expected_fit_pin or fitted.get("scope") != "scripted_l4a_fit":
        raise ValueError("fitted model differs from the expected pin")
    observations, scope = _observations(chains, expected_holdout_pin)
    training = fitted["training"]
    if scope["settings"] != training["settings"] or any(
        set(scope[field]) & set(training[field])
        for field in ("chain_ids", "families", "snapshot_pins", "raw_episodes", "raw_sources", "loaded_notes")
    ):
        raise ValueError("held-out scope crosses training or differs in level inventory")
    line, hinge = (_decode_model(fitted[name]) for name in ("line", "hinge"))
    losses = []
    for chain_id, points in observations.items():
        straight = sum((y - predict(line, x)) ** 2 for x, y in points) / len(points)
        segmented = sum((y - predict(hinge, x)) ** 2 for x, y in points) / len(points)
        losses.append((chain_id, straight, segmented))
    straight = sum(item[1] for item in losses) / len(losses)
    segmented = sum(item[2] for item in losses) / len(losses)
    return {"scope": "scripted_l4a_holdout", "scientific_result": False,
            "fit_sha256": expected_fit_pin, "holdout_sha256": expected_holdout_pin,
            "straight_mse": _rational(straight), "hinge_mse": _rational(segmented), "gain": _rational(straight - segmented),
            "chains": [{"id": chain_id, "straight_mse": _rational(a), "hinge_mse": _rational(b),
                        "gain": _rational(a - b)} for chain_id, a, b in losses]}


def _chain(name, shape, offset):
    levels = []
    for i in range(-3, 4):
        level = f"level-{i + 4}"
        notes = [{"id": f"{name}/{level}/{n}", "text": "a" * 10, "support": []} for n in range(32)]
        snapshot = {"cutoff": 6, "raw_before": [], "raw_after": [], "loaded_before": notes,
                    "loaded_after": [{"id": "after/" + note["id"], "text": "a" * (i + 4),
                                      "support": [], "parents": [note["id"]]} for note in notes]}
        counts = {"kink": 4 + 2 * abs(i), "linear": 7 + i, "inverted": 12 - 2 * abs(i)}
        levels.append({"setting": level, "snapshot": snapshot, "snapshot_pin": pin(snapshot),
                       "false_notes": counts[shape] + offset})
    return {"id": name, "family": "family/" + name, "levels": levels}


def fixture(shape):
    return ([_chain("train", shape, 0)], [_chain("test-a", shape, 1), _chain("test-b", shape, -1)])


def demo():
    report = {}
    fixtures = {shape: fixture(shape) for shape in ("kink", "linear", "inverted")}
    for shape, (training, holdout) in fixtures.items():
        fitted = fit_training(training, expected_training_pin=pin(training), knots=KNOTS)
        report[shape] = {"fit": fitted, "holdout": score_holdout(
            holdout, fitted, expected_holdout_pin=pin(holdout), expected_fit_pin=pin(fitted),
        )}
    kink = report["kink"]["fit"]
    _, inverted_holdout = fixtures["inverted"]
    report["kink_to_inverted"] = {"holdout": score_holdout(
        inverted_holdout, kink, expected_holdout_pin=pin(inverted_holdout), expected_fit_pin=pin(kink),
    )}
    return report


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
