"""Join scripted R2 observations to an independently pinned paired schedule."""

from unicodedata import normalize

from lab import adapter_lineage, r2_precision_math


SCHEDULE_FIELDS = "schema contrast unit control_arm treatment_arm scorer_sha256 clusters"
OBSERVATION_FIELDS = "cluster_id family_id case_id rerun_id seed opportunity_id arm status value"


def _fields(record, expected):
    if type(record) is not dict or record.keys() != set(expected.split()):
        raise ValueError("unexpected paired grid fields")


def _identifier(value):
    if type(value) is not str or not value or value != value.strip() or value != normalize("NFC", value):
        raise ValueError("paired grid IDs and units must be nonempty and canonical")
    return value


def _seed(value):
    if value is not None and type(value) is not int:
        raise ValueError("paired rerun seed must be an integer or null")
    return value


def _unique(items, message):
    if len(items) != len(set(items)):
        raise ValueError(message)


def _schedule(schedule):
    _fields(schedule, SCHEDULE_FIELDS)
    if schedule["schema"] != "r2_paired_schedule_v1" or schedule["contrast"] != "control_minus_treatment":
        raise ValueError("unknown paired schedule schema or contrast")
    _identifier(schedule["unit"])
    control, treatment = (_identifier(schedule[key]) for key in ("control_arm", "treatment_arm"))
    if control == treatment:
        raise ValueError("paired schedule needs two distinct arms")
    if schedule["scorer_sha256"] is not None:
        adapter_lineage._digest(schedule["scorer_sha256"], 64)
    clusters = schedule["clusters"]
    if type(clusters) is not list or not clusters:
        raise ValueError("paired schedule needs an ordered cluster list")

    expected, identities = {}, []
    for cluster in clusters:
        _fields(cluster, "cluster_id family_id case_id reruns")
        cluster_id, family, case = (_identifier(cluster[key]) for key in ("cluster_id", "family_id", "case_id"))
        identities.append((cluster_id, family, case))
        reruns = cluster["reruns"]
        if type(reruns) is not list or not reruns:
            raise ValueError("paired cluster needs an ordered rerun list")
        assigned = []
        for rerun in reruns:
            _fields(rerun, "rerun_id seed opportunity_id")
            rerun_id = _identifier(rerun["rerun_id"])
            seed = _seed(rerun["seed"])
            opportunity = _identifier(rerun["opportunity_id"])
            assigned.append((rerun_id, seed, opportunity))
            expected[(cluster_id, rerun_id)] = (family, case, seed, opportunity)
        for column in zip(*assigned, strict=True):
            present = tuple(value for value in column if value is not None)
            _unique(present, "paired reruns must have distinct IDs, seeds and opportunities within a cluster")
    for column in zip(*identities, strict=True):
        _unique(column, "paired clusters must have distinct cluster, family and case IDs")
    return clusters, control, treatment, expected


def _observations(observations, *, schedule_sha256, scorer_sha256, expected, arms):
    _fields(observations, "schema schedule_sha256 scorer_sha256 rows")
    if (observations["schema"] != "r2_paired_observations_v1" or observations["schedule_sha256"] != schedule_sha256
            or observations["scorer_sha256"] != scorer_sha256):
        raise ValueError("paired observation envelope does not bind schedule and scorer")
    if type(observations["rows"]) is not list:
        raise ValueError("paired observations need a row list")
    recorded = {}
    for row in observations["rows"]:
        _fields(row, OBSERVATION_FIELDS)
        cluster, family, case, rerun, opportunity, arm = (
            _identifier(row[key]) for key in ("cluster_id", "family_id", "case_id", "rerun_id", "opportunity_id", "arm")
        )
        seed = _seed(row["seed"])
        if arm not in arms or expected.get((cluster, rerun)) != (family, case, seed, opportunity):
            raise ValueError("paired observation does not match its frozen rerun identity")
        key = (cluster, rerun, arm)
        if key in recorded:
            raise ValueError("duplicate paired arm observation")
        status, value = row["status"], row["value"]
        if status == "scored":
            value = r2_precision_math._number(value)
        elif status not in ("censored", "missing") or value is not None:
            raise ValueError("unscored paired observations need an explicit status and null value")
        recorded[key] = status, value
    return recorded


def join(schedule, observations, *, schedule_sha256):
    """Return one ordered row per scheduled pair, with exact differences where scored."""
    adapter_lineage._digest(schedule_sha256, 64)
    clusters, control, treatment, expected = _schedule(schedule)
    recorded = _observations(observations, schedule_sha256=schedule_sha256, scorer_sha256=schedule["scorer_sha256"],
                             expected=expected, arms=(control, treatment))
    result = []
    for cluster in clusters:
        joined = []
        for rerun in cluster["reruns"]:
            key = (cluster["cluster_id"], rerun["rerun_id"])
            control_status, control_value = recorded.get((*key, control), ("unrecorded", None))
            treatment_status, treatment_value = recorded.get((*key, treatment), ("unrecorded", None))
            both_scored = control_status == treatment_status == "scored"
            joined.append({**rerun, "control_status": control_status, "treatment_status": treatment_status,
                           "difference": control_value - treatment_value if both_scored else None})
        result.append({**cluster, "reruns": joined})
    return result
