"""Host-side broker for public scripted L5 item delivery."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from secrets import token_hex
from types import MappingProxyType


PHASES = ("pre", "post")
CONDITIONS = ("environment:clean", "environment:disrupted", "neutral:clean", "neutral:disrupted")


@dataclass(frozen=True)
class ShardFixture:
    workers: tuple[str, ...]
    target: str
    item_ids: Mapping[tuple[str, str], str]
    canaries: Mapping[tuple[str, str], str] = field(repr=False)


def _unique_tokens(keys):
    assigned = {}
    used = set()
    for key in keys:
        token = token_hex(16)
        while token in used:
            token = token_hex(16)
        assigned[key] = token
        used.add(token)
    return assigned


def fixture(team_size):
    """Create one host-owned fixture with separate opaque item IDs and payloads."""
    if type(team_size) is not int or team_size not in (4, 8):
        raise ValueError("scripted shard fixture needs four or eight workers")
    workers = tuple(f"a{index}" for index in range(team_size))
    keys = [(worker, phase) for worker in workers for phase in PHASES]
    item_ids = {key: f"item-{value}" for key, value in _unique_tokens(keys).items()}
    canaries = {key: f"canary-{value}" for key, value in _unique_tokens(keys).items()}
    return ShardFixture(workers, workers[1], MappingProxyType(item_ids), MappingProxyType(canaries))


def dispatch(fixture, worker, condition, phase, request):
    """Dispatch one worker request under selectors established by the host."""
    if worker not in fixture.workers or condition not in CONDITIONS or phase not in PHASES:
        raise ValueError("invalid host shard session")
    if type(request) is not dict or request.keys() != {"item"} or type(request["item"]) is not str:
        return {"items": []}
    key = (worker, phase)
    expected_item = fixture.item_ids[key]
    environment = condition.startswith("environment:")
    removed = condition == "environment:disrupted" and worker == fixture.target and phase == "post"
    if request["item"] != expected_item or not environment or removed:
        return {"items": []}
    return {"items": [{"item": expected_item, "canary": fixture.canaries[key]}]}
