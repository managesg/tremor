"""Offline advisor contract for blocked dependencies in the topology bench."""

from dataclasses import dataclass

REQUEST_COST = 1
RESULT_COST = 1
DEFER = "defer_until_visible"


@dataclass(frozen=True)
class Request:
    """The advisor sees task IDs from a worker's blocked event, not answers."""

    worker: str
    task: str
    missing: tuple[str, ...]


def available(request: Request) -> str:
    """Recommend checking this task again once its dependencies are visible."""
    if not request.missing:
        raise ValueError("advice requires a blocked dependency")
    return DEFER


def unavailable(_request: Request) -> None:
    """Represent a failed consultation without any network or fallback calls."""
    return None
