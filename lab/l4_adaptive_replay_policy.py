"""Causal fixed and adaptive replay comparison on public scripted receipts."""

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tremor import night

from lab import l2_relay_control, l4b_recovery_observation, memory_replay
from lab.l4_adaptive_replay_control import replay_day


FIXTURE_CLOCK = ((0, 0), (1, 1), (2, 3))
FIXTURE_PINS = {
    0: "eb14cc1dffb39709e5e35958923761ea1ba3c8ff193089b45b0b9fc6d136ffec",
    1: "6f635ee4dea1ebd1c04340a735e705c037484c927293c9f42f08b1a2ac6e12af",
    2: "b3c8d32536cc9a318648df29ef031306864f5e3eba29fd5c9eaaad5a60d0472c",
}


@dataclass(frozen=True)
class Relay:
    path: Path
    roots: tuple[str, ...]
    head: str
    event_count: int


@dataclass(frozen=True)
class Window:
    closed_day: int
    available_day: int
    protocol: str
    horizon: int
    hold: int
    predicates: tuple[bool | None, ...]
    terminal: str
    relay: Relay | None


def _pin(value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def window_pin(window):
    """Bind one diagnostic, including its slot, independently of a local archive path."""
    relay = window.relay
    return _pin({
        "closed_day": window.closed_day, "available_day": window.available_day,
        "protocol": window.protocol, "horizon": window.horizon, "hold": window.hold,
        "predicates": window.predicates, "terminal": window.terminal,
        "relay": [relay.head, relay.event_count, sorted(relay.roots)] if relay else None,
    })


def _receipt(window):
    samples = [{"night": index, "predicate": predicate} for index, predicate in enumerate(window.predicates)]
    recovery = l4b_recovery_observation.classify(
        samples, horizon=window.horizon, hold=window.hold, terminal=window.terminal,
    )
    relay = window.relay
    counts = None
    relay_status = "missing_receipt" if relay is None else "no_eligible_roots"
    if relay is not None and relay.roots:
        score = l2_relay_control.measure(
            relay.path, planted_roots=relay.roots, expected_head=relay.head, expected_events=relay.event_count,
        )
        opening_roots = {
            event["data"]["id"] for event in score["trace"]
            if event["round"] == 0 and event["type"] == "post" and event["data"]["kind"] == "plant"
            and event["data"]["text"] == l2_relay_control.FALSE_STATEMENT
        }
        if set(relay.roots) != opening_roots:
            raise ValueError("relay diagnostic must include every opening plant")
        counts = score["first_generation_relay_counts"]
        relay_status = "observed"
    operational = window.terminal == "operational_stop"
    receipt = {
        "closed_day": window.closed_day, "available_day": window.available_day, "protocol": window.protocol,
        "horizon": window.horizon, "hold": window.hold, "recovery_status": recovery["status"],
        "recovery_terminal": window.terminal,
        "confirmed_recovery_night": None if operational else recovery["confirmation_night"],
        "recovery_input_sha256": _pin({"predicates": window.predicates, "terminal": window.terminal}),
        "relay_status": relay_status, "relay_head": relay.head if relay else None,
        "relay_event_count": relay.event_count if relay else None,
        "root_counts": counts,
    }
    return receipt | {"window_input_sha256": window_pin(window)}


def decide(windows, *, day, current, weaker, clock, expected_windows):
    """Hold or lower strength using the latest two comparable available windows."""
    windows = tuple(windows)
    slots = sorted(clock)
    if (any(type(closed) is not int or type(available) is not int or not 0 <= closed <= available
            for closed, available in slots) or len({closed for closed, _ in slots}) != len(slots)):
        raise ValueError("ambiguous diagnostic clock")
    visible = [(closed, available) for closed, available in slots if available < day]
    receipts = []
    for closed, available in visible[-2:]:
        matches = [row for row in windows if row.closed_day == closed]
        if len(matches) > 1 or (matches and matches[0].available_day != available):
            raise ValueError("diagnostic window differs from the trusted clock")
        if matches:
            window = matches[0]
            if window_pin(window) != expected_windows.get(closed):
                raise ValueError("diagnostic window differs from the trusted slot pin")
            receipts.append(_receipt(window))
        else:
            receipts.append({"closed_day": closed, "available_day": available, "status": "missing_window"})
    reason = "need_two_windows"
    strength = current
    if len(receipts) == 2:
        old, new = receipts
        comparison_fields = ("protocol", "horizon", "hold")
        if any(row.get("status") == "missing_window" for row in receipts):
            reason = "unknown_diagnostic"
        elif any(old[key] != new[key] for key in comparison_fields):
            reason = "incomparable_windows"
        elif any(row["confirmed_recovery_night"] is None or row["root_counts"] is None for row in receipts):
            reason = "unknown_diagnostic"
        elif len(old["root_counts"]) != len(new["root_counts"]):
            reason = "incomparable_windows"
        else:
            before, after = (Fraction(sum(row["root_counts"].values()), len(row["root_counts"])) for row in receipts)
            rises = (after > before, new["confirmed_recovery_night"] > old["confirmed_recovery_night"])
            if any(rises) and current > weaker:
                strength, reason = weaker, "both_diagnostics_rose" if all(rises) else "a_diagnostic_rose"
            else:
                reason = "no_lowering"
    return {"day": day, "strength": strength, "reason": reason, "diagnostics": receipts}


def compare(days, windows, *, clock, expected_windows, fixed_strength=1, weaker_strength=0, seed=17):
    """Use the same arrivals, sources and per-day seed in both development arms."""
    days = tuple(tuple(arrivals) for arrivals in days)
    windows = tuple(windows)
    clock = tuple(clock)
    expected_windows = dict(expected_windows)
    if (any(type(setting) not in (int, float) for setting in (fixed_strength, weaker_strength))
            or not 0 <= weaker_strength <= fixed_strength <= 1):
        raise ValueError("strength settings must be ordered within [0, 1]")
    sources = {}
    stores = {"fixed": [], "adaptive": []}
    strength = fixed_strength
    records = []
    for day, arrivals in enumerate(days, start=1):
        decision = decide(windows, day=day, current=strength, weaker=weaker_strength,
                          clock=clock, expected_windows=expected_windows)
        strength = decision["strength"]
        for note_id, _, source_text in arrivals:
            source_id = f"day-{day}:{note_id}"
            if source_id in sources:
                raise ValueError("duplicate daily source ID")
            sources[source_id] = source_text

        results = {}
        for arm, setting in (("fixed", fixed_strength), ("adaptive", strength)):
            store = stores[arm]
            for note_id, statement, _ in arrivals:
                store = night.add_note(store, note_id, statement, "scripted-worker", day, (f"day-{day}:{note_id}",))
            result = replay_day(store, day=day, source_prefix=sources, strength=setting, seed=seed + day)
            stores[arm] = result["store"]
            results[arm] = {"strength": setting, **result}
        records.append({"day": day, "decision": decision, "source_prefix_sha256": _pin(sources), "arms": results})
    return {"scope": "scripted_adaptive_replay", "scientific_result": False,
            "clock_sha256": _pin(sorted(clock)), "days": records}


def fixture(root):
    relays = []
    for name, emit in (("zero", False), ("positive", True)):
        path = root / f"relay-{name}.jsonl"
        result = l2_relay_control.control(path, emit_relays=emit)
        anchor = result["anchor"]
        relays.append(Relay(path, tuple(result["planted_roots"]), anchor["expected_head"], anchor["expected_events"]))
    zero, positive = relays
    stable = Window(0, 0, "fixed-development-window", 2, 1, (True, True, True), "window_complete", zero)
    another_stable = Window(1, 1, stable.protocol, 2, 1, stable.predicates, stable.terminal, zero)
    rise = Window(2, 3, stable.protocol, 2, 1, (False, True, True), stable.terminal, positive)
    days = (*memory_replay.DAY_NOTES, (memory_replay.PLANTED_NOTE, ("state", "state was ready", "state was ready")))
    return days, (stable, another_stable, rise)


def demo():
    with TemporaryDirectory(prefix="tremor-l4-adaptive-") as tmp:
        return compare(*fixture(Path(tmp)), clock=FIXTURE_CLOCK, expected_windows=FIXTURE_PINS)


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
