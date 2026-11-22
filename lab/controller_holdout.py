"""Verify independently pinned controller holdout exposure before paired analysis."""

import argparse
import hashlib
import json
from pathlib import Path

from lab import controller_selection as selection


SCHEMA = "controller_holdout_exposure_v1"
PRIOR_INVENTORY = "controller_prior_inventory_v1"
PRIOR_ROLES = ("development", "calibration", "controller_tuning", "baseline_tuning")
GROUP_FIELDS = ("family", "lineage", "seed_group")
MEMBER_FIELDS = (*GROUP_FIELDS, "prompt_sha256")


def _canonical(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _task_prompts(taskset):
    """Identify constituent prompts independently of labels, answers and task order."""
    tasks = taskset["tasks"]
    selection._require(type(tasks) is list and tasks, "missing holdout task content")
    prompts = [_canonical(selection._text(task["check"], "holdout task prompt")) for task in tasks]
    selection._require(len(prompts) == len(set(prompts)), "duplicate task prompt in holdout block")
    return sorted(prompts)


def _groups(row):
    return tuple(selection._text(row[field], field) for field in GROUP_FIELDS)


def _prompt_pins(value):
    selection._require(type(value) is list and value, "missing prompt digest inventory")
    values = [selection._digest(item) for item in value]
    selection._require(values == sorted(set(values)), "prompt digest inventory must be sorted and unique")
    return values


def _prior_data(bundle, document, selected, sources):
    enabled = selected["declared_enabled"]
    selection._object(sources, (*PRIOR_ROLES, *enabled), "prior exposure sources")
    prior_groups = [set() for _ in GROUP_FIELDS]
    prior_prompts = set()
    for role, record in sources.items():
        selection._object(record, ("source_sha256", "members"), "prior exposure source")
        pin = selection._digest(record["source_sha256"])
        if role in enabled:
            ref = document["lines"][role]["evidence"]
            receipt = selection._pinned_json(selection._reference(bundle, ref), ref["sha256"])
            selection._require(pin == receipt["artifacts"]["data"]["sha256"],
                               f"{role} prior exposure differs from the selected research data")
        rows = record["members"]
        selection._require(type(rows) is list and rows, f"missing exposure members for {role}")
        for row in rows:
            selection._object(row, MEMBER_FIELDS, "prior exposure member")
            for values, item in zip(prior_groups, _groups(row), strict=True):
                values.add(item)
            prior_prompts.update(_prompt_pins(row["prompt_sha256"]))
    return prior_groups, prior_prompts


def _holdout_rows(blocks, rows, family, prior):
    selection._require(type(blocks) is list and blocks and type(rows) is list and len(rows) == len(blocks),
                       "independent exposure must cover every scheduled block")
    prior_groups, prior_prompts = prior
    clusters, block_ids = {}, set()
    for block, row in zip(blocks, rows, strict=True):
        selection._object(row, ("block_id", "taskset_sha256", "cluster_id", *MEMBER_FIELDS), "holdout exposure row")
        identifier = selection._text(block["block_id"], "holdout block ID")
        selection._require(identifier not in block_ids and row["block_id"] == identifier,
                           "holdout exposure block identity or order differs")
        block_ids.add(identifier)
        groups = _groups(row)
        selection._require(groups[0] == family, "holdout family differs from the registered controller scope")
        taskset = block["taskset"]
        selection._require(taskset.get("split") == "heldout", "scheduled taskset is not declared held out")
        seed = block["seed"]
        selection._require(type(seed) is int and type(taskset.get("seed")) is int and taskset["seed"] == seed,
                           "holdout seed differs from the scheduled taskset")
        prompts = _prompt_pins(row["prompt_sha256"])
        selection._require(selection._digest(row["taskset_sha256"]) == _canonical(taskset)
                           and prompts == _task_prompts(taskset), "holdout exposure does not bind taskset bytes")
        for field, used, value in zip(GROUP_FIELDS, prior_groups, groups, strict=True):
            selection._require(value not in used, f"holdout {field} overlaps prior exposure")
        selection._require(prior_prompts.isdisjoint(prompts), "holdout prompt overlaps prior exposure")
        cluster = selection._text(row["cluster_id"], "holdout cluster")
        keys = [("lineage", groups[1]), ("seed group", groups[2]), ("scheduled seed", seed)]
        keys.extend(("task prompt", prompt) for prompt in prompts)
        for key in keys:
            selection._require(clusters.setdefault(key, cluster) == cluster,
                               f"repeated {key[0]} is split across holdout clusters")
    return len(set(clusters.values()))


def verify(bundle, manifest, evidence_index, task_inventory, witness, *, manifest_sha256, evidence_index_sha256,
           witness_sha256, prior_inventory=None):
    """Validate scope, coverage, and partition consistency at the supplied custody pin."""
    root = Path(bundle).resolve(strict=True)
    selected = selection.verify(root, manifest, evidence_index, manifest_sha256=manifest_sha256,
                                evidence_index_sha256=evidence_index_sha256)
    document = selection._pinned_json(manifest, manifest_sha256)
    task_pin = document["inputs"]["task_manifest_sha256"]
    inventory = selection._pinned_json(task_inventory, task_pin)
    selection._object(inventory, ("blocks",), "controller task inventory")
    custody = selection._pinned_json(witness, witness_sha256)
    selection._object(custody, ("schema", "manifest_sha256", "task_inventory_sha256", "prior", "holdout"),
                      "independent exposure witness")
    selection._require(custody["schema"] == SCHEMA and custody["manifest_sha256"] == manifest_sha256
                       and custody["task_inventory_sha256"] == task_pin, "exposure witness binds a different freeze")
    prior_pin = None
    if prior_inventory is not None:
        prior_path, prior_pin = prior_inventory
        independent = selection._pinned_json(prior_path, prior_pin)
        selection._object(independent, ("schema", "manifest_sha256", "roles"), "prior inventory")
        selection._require(independent["schema"] == PRIOR_INVENTORY
                           and independent["manifest_sha256"] == manifest_sha256,
                           "prior inventory refers to a different freeze")
        selection._require(independent["roles"] == custody["prior"],
                           "prior source or member inventory differs from the independent record")
    prior = _prior_data(root, document, selected, custody["prior"])
    clusters = _holdout_rows(inventory["blocks"], custody["holdout"], document["scope"]["task_family"], prior)
    report = {
        "evidence": "prospective_exposure_metadata",
        "manifest_sha256": manifest_sha256,
        "task_inventory_sha256": task_pin,
        "witness_sha256": witness_sha256,
        "heldout_blocks": len(inventory["blocks"]),
        "heldout_clusters": clusters,
        "scientific_acceptance": False,
    }
    if prior_pin is not None:
        report["prior_inventory_sha256"] = prior_pin
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "manifest", "evidence_index", "task_inventory", "witness"):
        parser.add_argument(name, type=Path)
    for name in ("manifest", "evidence-index", "witness"):
        parser.add_argument(f"--{name}-sha256", required=True)
    parser.add_argument("--prior-inventory", nargs=2, metavar=("PATH", "SHA256"))
    try:
        report = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
